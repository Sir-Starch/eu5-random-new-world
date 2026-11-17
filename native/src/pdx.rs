//! Span-preserving script parser. Offsets count Unicode scalar values like Python str.
//! The lexer and grammar equal tests/reference/pdx.py; construction is iterative.

use std::time::{Duration, Instant};

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Kind {
    Word,
    String,
    Op,
    Open,
    Close,
}

#[derive(Clone, Copy, Debug)]
pub struct Token {
    pub kind: Kind,
    pub byte: usize,
    pub stop: usize,
    pub start: usize,
    pub end: usize,
}

#[derive(Debug)]
pub enum Fault {
    Bad(usize, char),
    Value(usize, usize),
    Message(&'static str, usize),
    Deep,
}

#[derive(Debug)]
pub struct Entry {
    pub key: Option<usize>,
    pub op: Option<usize>,
    pub value: Value,
    pub start: usize,
    pub end: usize,
}

#[derive(Debug)]
pub enum Value {
    Scalar(usize),
    Block(usize),
}

#[derive(Debug)]
pub struct Block {
    pub entries: Vec<Entry>,
    pub open: Option<usize>,
    pub close: usize,
}

pub struct Parser {
    pub text: String,
    pub tokens: Vec<Token>,
    pub blocks: Vec<Block>,
    byte: usize,
    offset: usize,
    token: usize,
    stack: Vec<usize>,
    lexed: bool,
    finished: bool,
}

// Python's Unicode \s additionally includes the four ASCII information separators.
fn space(ch: char) -> bool {
    ch.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&ch)
}

fn word(ch: char) -> bool {
    !space(ch) && !matches!(ch, '{' | '}' | '=' | '<' | '>' | '!' | '?' | '#' | '"')
}

impl Parser {
    pub fn new(text: String) -> Self {
        Self {
            text,
            tokens: Vec::new(),
            blocks: vec![Block {
                entries: Vec::new(),
                open: None,
                close: 0,
            }],
            byte: 0,
            offset: 0,
            token: 0,
            stack: vec![0],
            lexed: false,
            finished: false,
        }
    }

    pub fn value(&self, token: usize) -> &str {
        let token = self.tokens[token];
        &self.text[token.byte..token.stop]
    }

    fn lex(&mut self) -> Result<(), Fault> {
        let tail = &self.text[self.byte..];
        let mut chars = tail.char_indices();
        let (_, ch) = chars.next().expect("nonempty lexer input");
        let mut bytes = ch.len_utf8();
        let mut length = 1;
        let kind = match ch {
            '#' => {
                for (at, ch) in chars {
                    if ch == '\n' {
                        break;
                    }
                    bytes = at + ch.len_utf8();
                    length += 1;
                }
                None
            }
            ch if space(ch) => {
                for (at, ch) in chars {
                    if !space(ch) {
                        break;
                    }
                    bytes = at + ch.len_utf8();
                    length += 1;
                }
                None
            }
            '"' => {
                let mut closed = false;
                while let Some((at, ch)) = chars.next() {
                    bytes = at + ch.len_utf8();
                    length += 1;
                    if ch == '"' {
                        closed = true;
                        break;
                    }
                    if ch == '\\' {
                        let Some((at, escaped)) = chars.next() else {
                            break;
                        };
                        if escaped == '\n' {
                            break;
                        }
                        bytes = at + escaped.len_utf8();
                        length += 1;
                    }
                }
                if !closed {
                    return Err(Fault::Bad(self.offset, '"'));
                }
                Some(Kind::String)
            }
            '{' => Some(Kind::Open),
            '}' => Some(Kind::Close),
            '=' | '<' | '>' | '!' | '?' => {
                if tail.as_bytes().get(1) == Some(&b'=') {
                    bytes = 2;
                    length = 2;
                } else if matches!(ch, '!' | '?') {
                    return Err(Fault::Bad(self.offset, ch));
                }
                Some(Kind::Op)
            }
            _ => {
                for (at, ch) in chars {
                    if !word(ch) {
                        break;
                    }
                    bytes = at + ch.len_utf8();
                    length += 1;
                }
                Some(Kind::Word)
            }
        };
        if let Some(kind) = kind {
            self.tokens.push(Token {
                kind,
                byte: self.byte,
                stop: self.byte + bytes,
                start: self.offset,
                end: self.offset + length,
            });
        }
        self.byte += bytes;
        self.offset += length;
        Ok(())
    }

    fn parse(&mut self) -> Result<(), Fault> {
        let at = self.token;
        let token = self.tokens[at];
        let block = *self.stack.last().expect("root remains on parser stack");
        if token.kind == Kind::Close {
            if block == 0 {
                return Err(Fault::Message("unbalanced closing brace", token.start));
            }
            self.blocks[block].close = token.start;
            self.stack.pop();
            let parent = *self.stack.last().expect("root remains on parser stack");
            self.blocks[parent].entries.last_mut().unwrap().end = token.start + 1;
            self.token += 1;
            return Ok(());
        }
        if token.kind == Kind::Op {
            return Err(Fault::Message("operator without a key", token.start));
        }
        let assigned = matches!(token.kind, Kind::Word | Kind::String)
            && self.tokens.get(at + 1).is_some_and(|t| t.kind == Kind::Op);
        let value_at = if assigned { at + 2 } else { at };
        let Some(value) = self.tokens.get(value_at).copied() else {
            return Err(Fault::Message(
                "assignment without a value",
                self.tokens[at + 1].start,
            ));
        };
        let parsed = match value.kind {
            Kind::Word | Kind::String => Value::Scalar(value_at),
            Kind::Open => {
                // Preserve the Python reference's recursion behavior on unusually
                // deep documents by letting that implementation handle them.
                if self.stack.len() >= 128 {
                    return Err(Fault::Deep);
                }
                let index = self.blocks.len();
                self.blocks.push(Block {
                    entries: Vec::new(),
                    open: Some(value.start),
                    close: 0,
                });
                self.stack.push(index);
                Value::Block(index)
            }
            _ => return Err(Fault::Value(value.start, value_at)),
        };
        self.blocks[block].entries.push(Entry {
            key: assigned.then_some(at),
            op: assigned.then_some(at + 1),
            value: parsed,
            start: token.start,
            end: value.end,
        });
        self.token = value_at + 1;
        Ok(())
    }

    /// Yield between small batches; a single token is indivisible.
    pub fn advance(&mut self, budget: Duration) -> Result<bool, Fault> {
        let started = Instant::now();
        loop {
            for _ in 0..1024 {
                if !self.lexed {
                    if self.byte == self.text.len() {
                        self.lexed = true;
                        self.blocks[0].close = self.offset;
                    } else {
                        self.lex()?;
                    }
                } else if self.token < self.tokens.len() {
                    self.parse()?;
                } else {
                    if self.stack.len() != 1 {
                        return Err(Fault::Message(
                            "unclosed block",
                            self.tokens.last().map_or(0, |t| t.start),
                        ));
                    }
                    self.finished = true;
                    return Ok(true);
                }
            }
            if started.elapsed() >= budget {
                return Ok(false);
            }
        }
    }

    pub fn finished(&self) -> bool {
        self.finished
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unicode_offsets_and_bare_blocks() {
        let mut parser = Parser::new("é = { \"中\" x >= 2 { y } }".to_owned());
        while !parser.advance(Duration::from_secs(1)).unwrap() {}
        assert_eq!(parser.blocks.len(), 3);
        assert_eq!(parser.blocks[1].open, Some(4));
        assert_eq!(parser.blocks[1].close, 23);
        assert_eq!(parser.blocks[0].entries[0].end, 24);
        assert_eq!(parser.value(2), "{");
    }

    #[test]
    fn lexical_errors_precede_structural_errors() {
        let mut parser = Parser::new("} !".to_owned());
        assert!(matches!(
            parser.advance(Duration::from_secs(1)),
            Err(Fault::Bad(2, '!'))
        ));
    }
}
