//! Random New World's window: a web view drawing the generator's state, and the bridge to the
//! generator (ADR 0011). `--self-test` starts the bridge, asks it for the window's first state
//! and exits without opening a window.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod bridge;

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

use serde_json::Value;
use tauri::{Emitter, Manager, RunEvent};

use bridge::{resolve, Bridge, Launch};

const CLOSE_WAIT: Duration = Duration::from_secs(15);

struct Shell(Arc<Bridge>);

#[tauri::command]
async fn rpc(
    method: String,
    params: Value,
    shell: tauri::State<'_, Shell>,
) -> Result<Value, String> {
    let bridge = Arc::clone(&shell.0);
    bridge.call(&method, params).await
}

fn launch() -> Result<Launch, String> {
    let program = std::env::current_exe().map_err(|e| e.to_string())?;
    let folder = program.parent().map(PathBuf::from).unwrap_or_default();
    let current = std::env::current_dir().unwrap_or_default();
    let python = std::env::var_os("RNW_PYTHON").map(PathBuf::from);
    resolve(&folder, &current, python).ok_or_else(|| {
        "The generator was not found beside the window, and RNW_PYTHON is not set".into()
    })
}

fn data_folder() -> Option<String> {
    std::env::var("RNW_DATA")
        .ok()
        .filter(|value| !value.is_empty())
}

fn self_test() -> i32 {
    let launch = match launch() {
        Ok(found) => found,
        Err(problem) => {
            eprintln!("{problem}");
            return 1;
        }
    };
    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_time()
        .build();
    let Ok(runtime) = runtime else { return 1 };
    let bridge = match Bridge::start(&launch, data_folder(), |_| {}, |_| {}) {
        Ok(started) => started,
        Err(problem) => {
            eprintln!("The generator did not start: {problem}");
            return 1;
        }
    };
    let answer = runtime.block_on(async {
        tokio::time::timeout(Duration::from_secs(120), bridge.call("hello", Value::Null)).await
    });
    bridge.stop(CLOSE_WAIT);
    match answer {
        Ok(Ok(hello)) => {
            let version = hello
                .pointer("/static/version")
                .and_then(Value::as_str)
                .unwrap_or("?");
            println!("Random New World {version}: window shell and bridge work");
            0
        }
        Ok(Err(problem)) => {
            eprintln!("The generator refused: {problem}");
            1
        }
        Err(_) => {
            eprintln!("The generator did not answer");
            1
        }
    }
}

fn main() {
    if std::env::args().any(|argument| argument == "--self-test") {
        std::process::exit(self_test());
    }
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![rpc])
        .setup(|app| {
            let launch = launch()?;
            let states = app.handle().clone();
            let ends = app.handle().clone();
            let bridge = Bridge::start(
                &launch,
                data_folder(),
                move |state| {
                    let _ = states.emit("rnw://state", state);
                },
                move |reason| {
                    let _ = ends.emit("rnw://ended", reason);
                },
            )?;
            app.manage(Shell(Arc::new(bridge)));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("the window could not be built");
    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(shell) = handle.try_state::<Shell>() {
                shell.0.stop(CLOSE_WAIT);
            }
        }
    });
}
