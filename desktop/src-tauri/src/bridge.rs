//! The generator behind the window: `python -m rnw.gui.bridge`, spoken to in JSON lines.
//!
//! The bridge answers requests (`{"id", "method", "params"}`) with `{"id", "result"}` or
//! `{"id", "error"}` and sends `{"event": "state", "data"}` whenever what the window draws
//! changes. This module starts it, writes the window's requests to it, completes each request
//! with its answer and hands the states to the window. Closing its input ends it: it cancels
//! running work and waits for it first.

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use serde_json::{json, Value};
use tokio::sync::oneshot;

type Answer = Result<Value, String>;

/// How to start the bridge: a program and its arguments, and the folder to start it in.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Launch {
    pub program: PathBuf,
    pub args: Vec<String>,
    pub folder: Option<PathBuf>,
}

const MODULE: [&str; 2] = ["-m", "rnw.gui.bridge"];

/// The interpreter of a packaged generator beside the window's program, if there is one: the
/// hub's `generator/python` (Windows) or a `generator/python/bin` of a Linux archive.
fn packaged(folder: &Path) -> Option<PathBuf> {
    let candidates = [
        folder.join("generator").join("python").join("python.exe"),
        folder
            .join("generator")
            .join("python")
            .join("bin")
            .join("python3"),
    ];
    candidates.into_iter().find(|path| path.is_file())
}

/// The source checkout above `start`, recognised by the bridge's own module.
fn checkout(start: &Path) -> Option<PathBuf> {
    start
        .ancestors()
        .find(|folder| folder.join("src/rnw/gui/bridge.py").is_file())
        .map(Path::to_path_buf)
}

/// Decide how to start the bridge. `RNW_PYTHON` names an interpreter that has the generator;
/// else a packaged one beside the program; else `uv run` in the source checkout (development).
pub fn resolve(program_folder: &Path, current: &Path, python: Option<PathBuf>) -> Option<Launch> {
    let flags = |list: &[&str]| -> Vec<String> {
        list.iter()
            .chain(MODULE.iter())
            .map(|s| (*s).to_string())
            .collect()
    };
    if let Some(program) = python {
        return Some(Launch {
            program,
            args: flags(&["-X", "utf8"]),
            folder: None,
        });
    }
    if let Some(program) = packaged(program_folder) {
        return Some(Launch {
            program,
            args: flags(&["-B", "-I", "-X", "utf8"]),
            folder: Some(program_folder.to_path_buf()),
        });
    }
    let root = checkout(program_folder).or_else(|| checkout(current))?;
    Some(Launch {
        program: PathBuf::from("uv"),
        args: ["run", "--quiet", "python"]
            .iter()
            .chain(MODULE.iter())
            .map(|s| (*s).to_string())
            .collect(),
        folder: Some(root),
    })
}

pub struct Bridge {
    child: Mutex<Option<Child>>,
    input: Mutex<Option<ChildStdin>>,
    pending: Arc<Mutex<HashMap<u64, oneshot::Sender<Answer>>>>,
    next: AtomicU64,
}

impl Bridge {
    /// Start the bridge; `on_state` receives every state it sends, `on_end` is called once when
    /// it stops answering.
    pub fn start(
        launch: &Launch,
        data: Option<String>,
        on_state: impl Fn(Value) + Send + 'static,
        on_end: impl Fn(String) + Send + 'static,
    ) -> std::io::Result<Self> {
        let mut command = Command::new(&launch.program);
        command.args(&launch.args);
        if let Some(folder) = data {
            command.arg("--data").arg(folder);
        }
        if let Some(folder) = &launch.folder {
            command.current_dir(folder);
        }
        command
            .env("PYTHONUNBUFFERED", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit());
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            command.creation_flags(CREATE_NO_WINDOW);
        }
        let mut child = command.spawn()?;
        let input = child.stdin.take();
        let output = child
            .stdout
            .take()
            .ok_or_else(|| std::io::Error::other("no stdout"))?;
        let pending: Arc<Mutex<HashMap<u64, oneshot::Sender<Answer>>>> = Arc::default();
        let waiting = Arc::clone(&pending);
        std::thread::Builder::new()
            .name("bridge-output".into())
            .spawn(move || {
                let reader = BufReader::new(output);
                for line in reader.lines() {
                    let Ok(line) = line else { break };
                    let Ok(message) = serde_json::from_str::<Value>(&line) else {
                        eprintln!("[bridge] not JSON: {line}");
                        continue;
                    };
                    if message.get("event").and_then(Value::as_str) == Some("state") {
                        on_state(message.get("data").cloned().unwrap_or(Value::Null));
                        continue;
                    }
                    let Some(id) = message.get("id").and_then(Value::as_u64) else {
                        continue;
                    };
                    let sender = waiting.lock().ok().and_then(|mut map| map.remove(&id));
                    if let Some(sender) = sender {
                        let answer = match message.get("error") {
                            Some(error) => Err(error.as_str().unwrap_or("error").to_string()),
                            None => Ok(message.get("result").cloned().unwrap_or(Value::Null)),
                        };
                        let _ = sender.send(answer);
                    }
                }
                let stranded: Vec<_> = waiting
                    .lock()
                    .map(|mut map| map.drain().collect())
                    .unwrap_or_default();
                for (_, sender) in stranded {
                    let _ = sender.send(Err("The generator stopped".into()));
                }
                on_end("The generator stopped".into());
            })?;
        Ok(Self {
            child: Mutex::new(Some(child)),
            input: Mutex::new(input),
            pending,
            next: AtomicU64::new(1),
        })
    }

    /// Ask the bridge; waits for its answer.
    pub async fn call(&self, method: &str, params: Value) -> Answer {
        let id = self.next.fetch_add(1, Ordering::Relaxed);
        let (sender, receiver) = oneshot::channel();
        self.pending
            .lock()
            .map_err(|e| e.to_string())?
            .insert(id, sender);
        let line = json!({ "id": id, "method": method, "params": params }).to_string();
        {
            let mut input = self.input.lock().map_err(|e| e.to_string())?;
            let stream = input.as_mut().ok_or("The generator has stopped")?;
            writeln!(stream, "{line}")
                .and_then(|()| stream.flush())
                .map_err(|e| format!("The generator stopped: {e}"))?;
        }
        receiver
            .await
            .map_err(|_| "The generator stopped".to_string())?
    }

    /// Close the bridge's input, so it cancels running work, and wait for it to end.
    pub fn stop(&self, patience: Duration) {
        if let Ok(mut input) = self.input.lock() {
            input.take();
        }
        let Ok(mut slot) = self.child.lock() else {
            return;
        };
        let Some(mut child) = slot.take() else { return };
        let began = Instant::now();
        while began.elapsed() < patience {
            if matches!(child.try_wait(), Ok(Some(_))) {
                return;
            }
            std::thread::sleep(Duration::from_millis(50));
        }
        let _ = child.kill();
        let _ = child.wait();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_interpreter_named_by_the_environment_comes_first() {
        let launch = resolve(
            Path::new("/nowhere"),
            Path::new("/nowhere"),
            Some("py".into()),
        );
        let launch = launch.expect("a launch");
        assert_eq!(launch.program, PathBuf::from("py"));
        assert_eq!(launch.args, ["-X", "utf8", "-m", "rnw.gui.bridge"]);
    }

    #[test]
    fn a_packaged_interpreter_beside_the_program_is_used_isolated() {
        let root = std::env::temp_dir().join(format!("rnw-shell-{}", std::process::id()));
        let python = root.join("generator").join("python").join("python.exe");
        std::fs::create_dir_all(python.parent().expect("a folder")).expect("folders");
        std::fs::write(&python, b"").expect("a file");
        let launch = resolve(&root, Path::new("/nowhere"), None).expect("a launch");
        assert_eq!(launch.program, python);
        assert_eq!(
            launch.args,
            ["-B", "-I", "-X", "utf8", "-m", "rnw.gui.bridge"]
        );
        std::fs::remove_dir_all(root).expect("cleanup");
    }

    #[test]
    fn the_source_checkout_runs_through_uv() {
        let here = Path::new(env!("CARGO_MANIFEST_DIR"));
        let launch = resolve(Path::new("/nowhere"), here, None).expect("a launch");
        assert_eq!(launch.program, PathBuf::from("uv"));
        assert!(launch
            .folder
            .expect("a folder")
            .join("pyproject.toml")
            .is_file());
    }
}
