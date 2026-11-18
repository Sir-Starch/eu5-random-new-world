//! The original tagged spline-list cursor, with the same first-fault byte offsets.

const OPEN: u16 = 3;
const CLOSE: u16 = 4;
const EQUALS: u16 = 1;
const KEY_ID: u16 = 0x0b;
const KEY_POINTS: u16 = 0x5f7;
const KEY_STRIPS: u16 = 0x5f6;
const KEY_SEGMENTS: u16 = 0x5f5;
const U32: u16 = 0x14;
const I64: u16 = 0x29c;

pub type Lists = (Vec<Vec<u32>>, Vec<(i64, Vec<u32>)>, usize);

struct Reader<'a> {
    data: &'a [u8],
    offset: usize,
}

impl Reader<'_> {
    fn bytes<const N: usize>(&mut self) -> Result<[u8; N], String> {
        let found = self
            .offset
            .checked_add(N)
            .and_then(|end| self.data.get(self.offset..end));
        let Some(found) = found else {
            return Err(format!("Spline network: truncated at byte {}", self.offset));
        };
        self.offset += N;
        Ok(found.try_into().expect("checked exact width"))
    }

    fn u16(&mut self) -> Result<u16, String> {
        self.bytes().map(u16::from_le_bytes)
    }

    fn u32(&mut self) -> Result<u32, String> {
        self.bytes().map(u32::from_le_bytes)
    }

    fn i64(&mut self) -> Result<i64, String> {
        self.bytes().map(i64::from_le_bytes)
    }

    fn peek(&mut self) -> Result<u16, String> {
        let offset = self.offset;
        let found = self.u16()?;
        self.offset = offset;
        Ok(found)
    }

    fn expect(&mut self, tokens: &[u16]) -> Result<(), String> {
        for &token in tokens {
            let offset = self.offset;
            let found = self.u16()?;
            if found != token {
                return Err(format!(
                    "Spline network: expected {token:#x}, found {found:#x} at byte {offset}"
                ));
            }
        }
        Ok(())
    }
}

pub fn parse(data: &[u8], offset: usize, segments: i32, strips: i32) -> Result<Lists, String> {
    let mut reader = Reader { data, offset };
    let mut found = Vec::new();
    // Do not reserve storage from untrusted counts: the next read can be truncated.
    for number in 0..segments.max(0) {
        reader.expect(&[OPEN, KEY_ID, EQUALS, I64])?;
        let id = reader.i64()?;
        if id != i64::from(number) << 8 {
            return Err(format!("Spline network: segment {number} has the id {id}"));
        }
        reader.expect(&[KEY_POINTS, EQUALS, OPEN])?;
        let mut points = Vec::new();
        while reader.peek()? == U32 {
            reader.expect(&[U32])?;
            points.push(reader.u32()?);
        }
        reader.expect(&[CLOSE, CLOSE])?;
        found.push(points);
    }
    reader.expect(&[CLOSE, KEY_STRIPS, EQUALS, OPEN])?;
    let mut mapped = Vec::new();
    let mut previous = -1;
    for _ in 0..strips.max(0) {
        reader.expect(&[OPEN, KEY_ID, EQUALS, I64])?;
        let id = reader.i64()?;
        if id <= previous {
            return Err("Spline network: the strips are not sorted by unique id".to_owned());
        }
        previous = id;
        reader.expect(&[KEY_SEGMENTS, EQUALS, OPEN])?;
        let mut references = Vec::new();
        while reader.peek()? == I64 {
            reader.expect(&[I64])?;
            let reference = reader.i64()?;
            if reference % 256 != 0 || reference < 0 || reference >> 8 >= i64::from(segments) {
                return Err(format!(
                    "Spline network: a strip names the segment {reference}, which does not exist"
                ));
            }
            references.push((reference >> 8) as u32);
        }
        reader.expect(&[CLOSE, CLOSE])?;
        mapped.push((id, references));
    }
    reader.expect(&[CLOSE])?;
    Ok((found, mapped, reader.offset))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tokens(values: &[u16]) -> Vec<u8> {
        values
            .iter()
            .flat_map(|value| value.to_le_bytes())
            .collect()
    }

    #[test]
    fn empty_lists_preserve_the_consumed_offset_and_trailing_bytes() {
        let mut data = tokens(&[CLOSE, KEY_STRIPS, EQUALS, OPEN, CLOSE]);
        data.extend_from_slice(&[0xff]);
        assert_eq!(parse(&data, 0, 0, 0), Ok((vec![], vec![], 10)));
        assert_eq!(parse(&data, 0, -1, -1), Ok((vec![], vec![], 10)));
        assert_eq!(
            parse(&data, usize::MAX, 0, 0).unwrap_err(),
            format!("Spline network: truncated at byte {}", usize::MAX)
        );
    }

    #[test]
    fn truncated_and_wrong_ids_fail_at_the_original_read() {
        let mut data = tokens(&[OPEN, KEY_ID, EQUALS, I64]);
        assert_eq!(
            parse(&data, 0, i32::MAX, 0).unwrap_err(),
            "Spline network: truncated at byte 8"
        );
        data.extend_from_slice(&256_i64.to_le_bytes());
        assert_eq!(
            parse(&data, 0, 1, 0).unwrap_err(),
            "Spline network: segment 0 has the id 256"
        );
    }
}
