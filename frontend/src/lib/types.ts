export type Fragment = {
  fragment_id: string;
  index: number;
  sequence: string;
  length_nt: number;
  gc_percent: number;
  max_homopolymer: number;
  encoding_variant: number;
  ecc: boolean;
  status: "VALID" | "WARNING" | "INVALID";
};

export type EncodeResponse = {
  encoding_version: string;
  result_id: string;
  file: {
    original_filename: string;
    original_extension: string;
    original_size: number;
    sha256_original: string;
  };
  stats: {
    fragment_count: number;
    total_nucleotides: number;
    gc_average: number;
    gc_min_observed: number;
    gc_max_observed: number;
    max_homopolymer_observed: number;
    original_size: number;
    compressed_size: number;
    compression_ratio: number;
    compression: boolean;
    fragments_valid: number;
    fragments_warning: number;
    fragments_invalid: number;
  };
  roundtrip: {
    result: "PASS" | "FAIL";
    sha256_original: string;
    sha256_reconstructed: string | null;
    reconstructed_size: number | null;
    message: string;
    bit_identical: boolean;
  };
  fragments_preview: Fragment[];
  fragment_count: number;
  synthesis_review_required: boolean;
  export_allowed: boolean;
  export_warning: string | null;
  qc_message: string;
  profile: string;
};

export type ApiError = {
  error?: string;
  detail?: string | { msg: string }[];
};

export type DecodeResponse = {
  decode_id: string;
  filename: string;
  size: number;
  sha256: string;
  sha256_original: string | null;
  sha256_matched: boolean | null;
  fragment_count: number;
  compression: boolean;
  ecc: boolean;
  download_url: string;
};

