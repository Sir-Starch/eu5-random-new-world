//! SplitMix64 lattice hashing, bit-identical to `rnw.rng`.

pub const GAMMA: u64 = 0x9E37_79B9_7F4A_7C15;
pub const MUL1: u64 = 0xBF58_476D_1CE4_E5B9;
pub const MUL2: u64 = 0x94D0_49BB_1331_11EB;
pub const X_MUL: u64 = 0xD6E8_FEB8_6659_FD93;
pub const Y_MUL: u64 = 0xA076_1D64_78BD_642F;

/// The SplitMix64 output function.
#[inline]
pub fn mix64(value: u64) -> u64 {
    let mut z = value;
    z = (z ^ (z >> 30)).wrapping_mul(MUL1);
    z = (z ^ (z >> 27)).wrapping_mul(MUL2);
    z ^ (z >> 31)
}

/// Hash of one integer lattice point; negative coordinates wrap as two's complement.
#[inline]
pub fn hash_point(key: u64, x: i64, y: i64) -> u64 {
    let z = key ^ (x as u64).wrapping_mul(X_MUL) ^ (y as u64).wrapping_mul(Y_MUL);
    mix64(z.wrapping_add(GAMMA))
}

#[cfg(test)]
mod tests {
    use super::*;

    // Values computed with `rnw.rng.hash_point` and `rnw.rng.mix64`.
    #[test]
    fn matches_the_python_reference() {
        assert_eq!(mix64(0), 0);
        assert_eq!(hash_point(0, 0, 0), mix64(GAMMA));
        assert_eq!(mix64(GAMMA), 0xe220_a839_7b1d_cdaf);
        assert_eq!(hash_point(12345, -7, 99), 0x3faa_e2b1_ae01_ae3b);
        assert_eq!(
            hash_point(u64::MAX, 1 << 40, -(1 << 40)),
            0x3c6d_37e1_b025_660e
        );
    }
}
