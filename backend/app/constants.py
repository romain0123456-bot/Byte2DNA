"""Central constants for BYTE2DNA-POC-1."""

ENCODING_VERSION = "BYTE2DNA-POC-1"
APPLICATION_NAME = "Byte2DNA"
PROFILE_NAME = "Generic POC"

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}
ALLOWED_FRAGMENT_LENGTHS = (100, 150, 200)

DEFAULT_FRAGMENT_LENGTH = 150
DEFAULT_GC_MIN = 40.0
DEFAULT_GC_MAX = 60.0
DEFAULT_HOMOPOLYMER_MAX = 3
DEFAULT_COMPRESSION = True
DEFAULT_ECC = True
DEFAULT_INCLUDE_SHA256_EXPORT = True

# 2-bit mapping used after scrambling.
BASE_TO_BITS = {"A": "00", "C": "01", "G": "10", "T": "11"}
BITS_TO_BASE = {"00": "A", "01": "C", "10": "G", "11": "T"}
BASES = "ACGT"

# Variant header: 8 nt, 1 bit/nt, GC-balanced, no homopolymers.
VARIANT_HEADER_NT = 8
MAX_VARIANTS = 256
INDEX_BYTES = 4
ECC_NSYM = 8
INNER_MAGIC = b"B2D1"

GC_WARNING_MARGIN = 5.0
HOMOPOLYMER_WARNING_EXTRA = 1

# In-memory export cache lifetime is process-local (POC, no database).
RESULT_CACHE_LIMIT = 128
