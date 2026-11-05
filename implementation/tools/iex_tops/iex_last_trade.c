/* IEX HIST (TOPS 1.6, IEX-TP v1) last regular-session trade per requested symbol, read from a decompressed pcap / pcap-ng
   stream on stdin. Usage: iex_last_trade <symbols-file> <session-start-ns> <session-end-ns>
   Output (stdout, consumed in memory by the caller, never logged): one line per requested symbol
     SYMBOL \t status \t price_e4 \t timestamp_ns \t regular_trades
   status: ROUND (last regular-session trade without the odd-lot flag), ODD_ONLY (only odd-lot trades in the session),
   NO_TRADE (no regular-session trade). Extended-hours flagged trades and trades outside [start, end) are ignored.
   Extra columns (listing diagnostics, no prices): security-directory seen 0/1, last trading status (T/H/P/O or -), trades
   in any session.
   A summary line "#STATS ..." goes to stderr (counts only).
   The mode above (the Universe504 mode) is unchanged by the full-symbol mode below: same arguments, same output bytes.

   FULL-SYMBOL MODE (explicit, opt-in):
     iex_last_trade --all-symbols <session-start-ns> <session-end-ns>
                    [--max-symbols N] [--source-bytes N] [--source-sha256 HEX64] [--no-stdin-sha256]
   No symbols file: every symbol seen in a TOPS symbol message gets a row, in a growing hash table with a hard ceiling
   (default 50000 distinct symbols, --max-symbols 1..1000000). Exceeding the ceiling writes NOTHING to stdout, prints
   "#ERROR SYMBOL_CEILING_EXCEEDED" to stderr and exits 6 (never a truncated table).
   Output (stdout only): JSON lines, one {"record":"symbol",...} per symbol sorted by the raw 8-byte symbol, then exactly one
   {"record":"summary",...} line (counts, stdin byte count + SHA-256, the caller's source bytes / SHA-256 echoed, parser
   version, mode, ceiling, completeness flags). Directory, trading status and the last round-lot regular-session trade are
   recorded separately; nothing here decides tradable / listed / eligible. stderr carries named errors only, never values.
   Exit codes: 2 bad arguments, 3 no capture header, 4 bad pcap-ng block, 5 unknown capture format, 6 symbol ceiling
   exceeded, 8 out of memory, 9 stdout write failed. A capture cut mid-record still writes the rows, with
   "truncated":true / "complete":false. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAXSYM 1024
typedef struct { char sym[9]; uint64_t key; int64_t round_px, odd_px; uint64_t round_ts, odd_ts, n, all_trades; int dir_seen; char status; } Rec;
static Rec recs[MAXSYM]; static int nrec = 0;
static int64_t T0, T1;
static uint64_t n_packets = 0, n_segments = 0, n_messages = 0, n_trades = 0, n_bad = 0;

static uint64_t key8(const unsigned char *p) { uint64_t k; memcpy(&k, p, 8); return k; }
static Rec *find(uint64_t k) { for (int i = 0; i < nrec; i++) if (recs[i].key == k) return &recs[i]; return NULL; }
static uint16_t le16(const unsigned char *p) { return (uint16_t)(p[0] | p[1] << 8); }
static uint32_t le32(const unsigned char *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
static uint64_t le64(const unsigned char *p) { return (uint64_t)le32(p) | (uint64_t)le32(p + 4) << 32; }

static void segment(const unsigned char *p, size_t len) {
  if (len < 40 || p[0] != 1) { n_bad++; return; }
  uint16_t proto = le16(p + 2), plen = le16(p + 12), count = le16(p + 14);
  if (proto != 0x8003 && proto != 0x8004) return;  /* TOPS / DEEP */
  n_segments++;
  const unsigned char *m = p + 40, *end = p + 40 + plen;
  if (end > p + len) { n_bad++; return; }
  for (uint16_t i = 0; i < count && m + 2 <= end; i++) {
    uint16_t ml = le16(m); const unsigned char *d = m + 2; m = d + ml;
    if (m > end) { n_bad++; return; }
    n_messages++;
    if (ml >= 18 && (d[0] == 0x44 || d[0] == 0x48)) {  /* Security Directory / Trading Status: listing diagnostics only */
      Rec *q = find(key8(d + 10)); if (q) { if (d[0] == 0x44) q->dir_seen = 1; else q->status = (char)d[1]; }
      continue;
    }
    if (ml < 38 || d[0] != 0x54) continue;  /* Trade Report */
    n_trades++;
    uint8_t flags = d[1]; uint64_t ts = le64(d + 2);
    { Rec *q = find(key8(d + 10)); if (q) q->all_trades++; }
    if (flags & 0x40) continue;  /* extended hours */
    if ((int64_t)ts < T0 || (int64_t)ts >= T1) continue;
    Rec *r = find(key8(d + 10)); if (!r) continue;
    int64_t px = (int64_t)le64(d + 22);
    r->n++;
    if (flags & 0x20) { if (ts >= r->odd_ts) { r->odd_ts = ts; r->odd_px = px; } }
    else if (ts >= r->round_ts) { r->round_ts = ts; r->round_px = px; }
  }
}
static void (*seg_fn)(const unsigned char *, size_t) = segment;
static void packet(const unsigned char *p, size_t len) {
  n_packets++;
  if (len < 14) return;
  size_t off = 12; uint16_t et = (uint16_t)(p[off] << 8 | p[off + 1]); off += 2;
  while (et == 0x8100 && len >= off + 4) { et = (uint16_t)(p[off + 2] << 8 | p[off + 3]); off += 4; }
  if (et != 0x0800 || len < off + 20) return;
  size_t ihl = (size_t)(p[off] & 0x0f) * 4; if (p[off + 9] != 17 || len < off + ihl + 8) return;
  off += ihl + 8;  /* UDP header */
  seg_fn(p + off, len - off);
}

static unsigned char *buf; static size_t cap = 1 << 24;
static char iobuf[1 << 22];

/* ---- SHA-256 (FIPS 180-4) of the stdin bytes, full-symbol mode only ---- */
typedef struct { uint32_t h[8]; uint64_t len; unsigned char blk[64]; size_t n; } Sha256;
static const uint32_t K256[64] = {
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01,
  0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
  0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
  0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08,
  0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
#define ROR(x, k) (((x) >> (k)) | ((x) << (32 - (k))))
static void sha_block(Sha256 *s, const unsigned char *p) {
  uint32_t w[64], a, b, c, d, e, f, g, h;
  for (int i = 0; i < 16; i++) w[i] = (uint32_t)p[4 * i] << 24 | (uint32_t)p[4 * i + 1] << 16 | (uint32_t)p[4 * i + 2] << 8 | p[4 * i + 3];
  for (int i = 16; i < 64; i++) {
    uint32_t s0 = ROR(w[i - 15], 7) ^ ROR(w[i - 15], 18) ^ (w[i - 15] >> 3), s1 = ROR(w[i - 2], 17) ^ ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
    w[i] = w[i - 16] + s0 + w[i - 7] + s1;
  }
  a = s->h[0]; b = s->h[1]; c = s->h[2]; d = s->h[3]; e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
  for (int i = 0; i < 64; i++) {
    uint32_t t1 = h + (ROR(e, 6) ^ ROR(e, 11) ^ ROR(e, 25)) + ((e & f) ^ (~e & g)) + K256[i] + w[i];
    uint32_t t2 = (ROR(a, 2) ^ ROR(a, 13) ^ ROR(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
    h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
  }
  s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d; s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}
static void sha_init(Sha256 *s) {
  static const uint32_t iv[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
  memcpy(s->h, iv, sizeof iv); s->len = 0; s->n = 0;
}
static void sha_update(Sha256 *s, const unsigned char *p, size_t n) {
  s->len += n;
  if (s->n) { size_t k = 64 - s->n < n ? 64 - s->n : n; memcpy(s->blk + s->n, p, k); s->n += k; p += k; n -= k; if (s->n == 64) { sha_block(s, s->blk); s->n = 0; } }
  while (n >= 64) { sha_block(s, p); p += 64; n -= 64; }
  if (n) { memcpy(s->blk, p, n); s->n = n; }
}
static void sha_hex(Sha256 *s, char out[65]) {
  uint64_t bits = s->len * 8; unsigned char pad = 0x80, z = 0, l8[8];
  sha_update(s, &pad, 1);
  while (s->n != 56) sha_update(s, &z, 1);
  for (int i = 0; i < 8; i++) l8[i] = (unsigned char)(bits >> (56 - 8 * i));
  sha_update(s, l8, 8);
  for (int i = 0; i < 8; i++) sprintf(out + 8 * i, "%08x", s->h[i]);
  out[64] = 0;
}

/* Input accounting (the Universe504 mode never prints it). A read that gets some but not all of the bytes it asked for
   is a capture cut mid-record. */
static uint64_t in_bytes = 0; static int in_partial = 0, in_truncated = 0, hashing = 0; static Sha256 in_sha;
static int readn(void *dst, size_t n) {
  size_t got = fread(dst, 1, n, stdin);
  in_bytes += got;
  if (hashing && got) sha_update(&in_sha, dst, got);
  if (got && got < n) in_partial = 1;
  return got == n;
}
static uint64_t n_caplen_short = 0;
static const char *capture_format = "none";

/* Reads the whole capture from stdin, calling packet() per frame. Returns 0, or the exit code of a fatal input error. */
static int read_capture(void) {
  setvbuf(stdin, iobuf, _IOFBF, sizeof iobuf);
  buf = malloc(cap);
  unsigned char hdr[24]; if (!readn(hdr, 4)) return 3;
  uint32_t magic = le32(hdr);
  if (magic == 0x0A0D0D0A) {  /* pcap-ng */
    capture_format = "pcapng";
    uint32_t type = magic;
    for (;;) {
      unsigned char l4[4]; if (!readn(l4, 4)) { in_truncated = 1; break; }
      uint32_t tl = le32(l4); if (tl < 12) return 4;
      size_t body = tl - 8; if (body > cap) { cap = body; buf = realloc(buf, cap); }
      if (!readn(buf, body)) { in_truncated = 1; break; }
      if (type == 6 && body >= 24) {
        uint32_t caplen = le32(buf + 12);
        if (20 + (size_t)caplen <= body) { if (caplen < le32(buf + 16)) n_caplen_short++; packet(buf + 20, caplen); }
      }
      else if (type == 3 && body >= 8) { uint32_t olen = le32(buf); packet(buf + 4, olen < body - 8 ? olen : body - 8); }
      unsigned char t4[4]; if (!readn(t4, 4)) break; type = le32(t4);
    }
  } else if (magic == 0xA1B2C3D4 || magic == 0xA1B23C4D) {  /* classic pcap, little endian */
    capture_format = "pcap";
    if (!readn(hdr + 4, 20)) return 3;
    unsigned char rh[16];
    while (readn(rh, 16)) {
      uint32_t incl = le32(rh + 8); if (incl > cap) { cap = incl; buf = realloc(buf, cap); }
      if (!readn(buf, incl)) { in_truncated = 1; break; }
      if (incl < le32(rh + 12)) n_caplen_short++;
      packet(buf, incl);
    }
  } else { fprintf(stderr, "#ERROR unknown capture format\n"); return 5; }
  if (in_partial) in_truncated = 1;
  return 0;
}

static int main_all_symbols(int argc, char **argv);

int main(int argc, char **argv) {
  if (argc >= 2 && strcmp(argv[1], "--all-symbols") == 0) return main_all_symbols(argc, argv);
  if (argc != 4) { fprintf(stderr, "usage\n"); return 2; }
  T0 = strtoll(argv[2], NULL, 10); T1 = strtoll(argv[3], NULL, 10);
  FILE *sf = fopen(argv[1], "r"); if (!sf) return 2;
  char line[64];
  while (fgets(line, sizeof line, sf) && nrec < MAXSYM) {
    line[strcspn(line, "\r\n")] = 0; if (!line[0] || strlen(line) > 8) continue;
    Rec *r = &recs[nrec++]; memset(r, 0, sizeof *r); memset(r->sym, ' ', 8); memcpy(r->sym, line, strlen(line));
    r->key = key8((unsigned char *)r->sym); r->sym[strlen(line)] = 0;
  }
  fclose(sf);
  { int rc = read_capture(); if (rc) return rc; }
  int round = 0, odd = 0, none = 0;
  for (int i = 0; i < nrec; i++) {
    Rec *r = &recs[i];
    if (r->round_ts) { round++; printf("%s\tROUND\t%lld\t%llu\t%llu\t%d\t%c\t%llu\n", r->sym, (long long)r->round_px, (unsigned long long)r->round_ts, (unsigned long long)r->n, r->dir_seen, r->status ? r->status : '-', (unsigned long long)r->all_trades); }
    else if (r->odd_ts) { odd++; printf("%s\tODD_ONLY\t%lld\t%llu\t%llu\t%d\t%c\t%llu\n", r->sym, (long long)r->odd_px, (unsigned long long)r->odd_ts, (unsigned long long)r->n, r->dir_seen, r->status ? r->status : '-', (unsigned long long)r->all_trades); }
    else { none++; printf("%s\tNO_TRADE\t0\t0\t0\t%d\t%c\t%llu\n", r->sym, r->dir_seen, r->status ? r->status : '-', (unsigned long long)r->all_trades); }
  }
  fprintf(stderr, "#STATS packets=%llu segments=%llu messages=%llu trades=%llu bad=%llu symbols=%d round=%d odd_only=%d no_trade=%d\n",
          (unsigned long long)n_packets, (unsigned long long)n_segments, (unsigned long long)n_messages, (unsigned long long)n_trades,
          (unsigned long long)n_bad, nrec, round, odd, none);
  return 0;
}

/* ======================================== FULL-SYMBOL MODE (--all-symbols) ======================================== */
#define FULL_PARSER_VERSION "2026-11-05.1"
#define FULL_DEFAULT_CEILING 50000
#define FULL_MAX_CEILING 1000000
typedef struct {
  unsigned char sym[8];                       /* the raw 8 symbol bytes as sent (space padded) */
  uint64_t key, msgs, dir_msgs, status_msgs, quotes, trade_reports, round_regular, odd_regular, excluded, breaks, other;
  uint64_t dir_ts, status_ts, last_ts, last_id;
  int64_t last_px; uint32_t round_lot, last_size;
  int has_round_lot, has_last, last_broken; unsigned char dir_flags, status, reason[4];
} FRec;
static FRec *frecs; static size_t nfrec = 0, frec_cap = 0;
static uint32_t *fidx; static size_t fidx_cap = 0;   /* open addressing, slot = record index + 1, 0 = empty */
static size_t f_ceiling = FULL_DEFAULT_CEILING;
static uint64_t f_dir = 0, f_status = 0, f_quotes = 0, f_breaks = 0, f_symbol_msgs = 0, f_short_symbol_msgs = 0;
static uint64_t seq_gaps = 0, seq_gap_msgs = 0, seq_regressions = 0, seq_stream_changes = 0, seq_next = 0;
static uint32_t seq_channel = 0, seq_session = 0; static int seq_have = 0; static uint64_t seq_first = 0;

static void fail(int code, const char *name) { fprintf(stderr, "#ERROR %s\n", name); exit(code); }
static uint64_t mix(uint64_t k) { k ^= k >> 33; k *= 0xff51afd7ed558ccdULL; k ^= k >> 33; k *= 0xc4ceb9fe1a85ec53ULL; return k ^ (k >> 33); }
static void fidx_put(size_t i) {
  size_t m = fidx_cap - 1, h = (size_t)mix(frecs[i].key) & m;
  while (fidx[h]) h = (h + 1) & m;
  fidx[h] = (uint32_t)(i + 1);
}
static FRec *fget(const unsigned char *s) {
  uint64_t k = key8(s);
  size_t m = fidx_cap - 1, h = (size_t)mix(k) & m;
  for (uint32_t j; (j = fidx[h]); h = (h + 1) & m) if (frecs[j - 1].key == k) return &frecs[j - 1];
  if (nfrec >= f_ceiling) {
    fprintf(stderr, "#ERROR SYMBOL_CEILING_EXCEEDED ceiling=%zu\n", f_ceiling);
    exit(6);                                   /* fail closed: nothing has been written to stdout */
  }
  if (nfrec == frec_cap) {
    frec_cap = frec_cap ? frec_cap * 2 : 4096;
    FRec *n = realloc(frecs, frec_cap * sizeof *frecs); if (!n) fail(8, "OUT_OF_MEMORY"); frecs = n;
  }
  FRec *r = &frecs[nfrec]; memset(r, 0, sizeof *r); memcpy(r->sym, s, 8); r->key = k;
  nfrec++;
  if (nfrec * 2 > fidx_cap) {                  /* keep the load factor at or under 1/2 */
    free(fidx); fidx_cap *= 2; fidx = calloc(fidx_cap, sizeof *fidx); if (!fidx) fail(8, "OUT_OF_MEMORY");
    for (size_t i = 0; i < nfrec; i++) fidx_put(i);
  } else fidx_put(nfrec - 1);
  return r;
}
static int symbol_type(unsigned char t) {    /* TOPS 1.6 messages carrying a symbol at byte 10 */
  switch (t) { case 0x41: case 0x42: case 0x44: case 0x45: case 0x48: case 0x4F: case 0x50: case 0x51: case 0x54: case 0x58: return 1; }
  return 0;
}

static void segment_all(const unsigned char *p, size_t len) {
  if (len < 40 || p[0] != 1) { n_bad++; return; }
  uint16_t proto = le16(p + 2), plen = le16(p + 12), count = le16(p + 14);
  if (proto != 0x8003 && proto != 0x8004) return;  /* TOPS / DEEP */
  n_segments++;
  const unsigned char *m = p + 40, *end = p + 40 + plen;
  if (end > p + len) { n_bad++; return; }
  uint32_t channel = le32(p + 4), session = le32(p + 8); uint64_t first = le64(p + 24);
  if (!seq_have || channel != seq_channel || session != seq_session) {
    if (seq_have) seq_stream_changes++; else seq_first = first;
    seq_have = 1; seq_channel = channel; seq_session = session; seq_next = first + count;
  } else {
    if (first > seq_next) { seq_gaps++; seq_gap_msgs += first - seq_next; }
    else if (first < seq_next) seq_regressions++;
    if (first + count > seq_next) seq_next = first + count;
  }
  for (uint16_t i = 0; i < count && m + 2 <= end; i++) {
    uint16_t ml = le16(m); const unsigned char *d = m + 2; m = d + ml;
    if (m > end) { n_bad++; return; }
    n_messages++;
    if (ml < 1 || !symbol_type(d[0])) continue;
    if (ml < 18) { f_short_symbol_msgs++; continue; }
    f_symbol_msgs++;
    FRec *r = fget(d + 10);
    r->msgs++;
    switch (d[0]) {
      case 0x44:                                 /* Security Directory: observation only */
        f_dir++; r->dir_msgs++; r->dir_flags = d[1]; r->dir_ts = le64(d + 2);
        if (ml >= 22) { r->round_lot = le32(d + 18); r->has_round_lot = 1; }
        break;
      case 0x48:                                 /* Trading Status: the last one in stream order */
        f_status++; r->status_msgs++; r->status = d[1]; r->status_ts = le64(d + 2);
        if (ml >= 22) memcpy(r->reason, d + 18, 4); else memset(r->reason, ' ', 4);
        break;
      case 0x51: f_quotes++; r->quotes++; break;  /* Quote Update: counted, no quote value kept */
      case 0x54: {                               /* Trade Report */
        if (ml < 38) { r->other++; break; }
        n_trades++; r->trade_reports++;
        uint8_t flags = d[1]; uint64_t ts = le64(d + 2);
        if ((flags & 0x40) || (int64_t)ts < T0 || (int64_t)ts >= T1) { r->excluded++; break; }
        if (flags & 0x20) { r->odd_regular++; break; }   /* odd lot: never the round-lot last trade */
        r->round_regular++;
        if (!r->has_last || ts >= r->last_ts) {
          r->has_last = 1; r->last_broken = 0; r->last_ts = ts; r->last_size = le32(d + 18);
          r->last_px = (int64_t)le64(d + 22); r->last_id = le64(d + 30);
        }
        break;
      }
      case 0x42:                                 /* Trade Break: flags the last trade when it is the one broken */
        f_breaks++; r->breaks++;
        if (ml >= 38 && r->has_last && le64(d + 30) == r->last_id) r->last_broken = 1;
        break;
      default: r->other++;
    }
  }
}

static void json_bytes(const unsigned char *s, size_t n) {  /* trailing pad spaces dropped; any other byte kept, escaped */
  while (n && s[n - 1] == ' ') n--;
  putchar('"');
  for (size_t i = 0; i < n; i++) {
    unsigned char c = s[i];
    if (c == '"' || c == '\\') { putchar('\\'); putchar(c); }
    else if (c < 0x20 || c > 0x7e) printf("\\u%04x", c);
    else putchar(c);
  }
  putchar('"');
}
static int frec_cmp(const void *a, const void *b) { return memcmp(((const FRec *)a)->sym, ((const FRec *)b)->sym, 8); }
static int parse_u64(const char *s, uint64_t *out) {
  if (!s || !*s) return 0;
  uint64_t v = 0;
  for (const char *c = s; *c; c++) { if (*c < '0' || *c > '9' || v > (UINT64_MAX - 9) / 10) return 0; v = v * 10 + (uint64_t)(*c - '0'); }
  *out = v; return 1;
}
static int hex64(const char *s, char out[65]) {
  if (!s || strlen(s) != 64) return 0;
  for (int i = 0; i < 64; i++) {
    char c = s[i];
    if (c >= 'A' && c <= 'F') c = (char)(c - 'A' + 'a');
    if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return 0;
    out[i] = c;
  }
  out[64] = 0; return 1;
}
#define B(x) ((x) ? "true" : "false")

static int main_all_symbols(int argc, char **argv) {
  uint64_t t0, t1, v, src_bytes = 0; int have_src_bytes = 0, have_src_sha = 0, stdin_sha = 1; char src_sha[65];
  if (argc < 4 || !parse_u64(argv[2], &t0) || !parse_u64(argv[3], &t1) || t0 >= t1 || t1 > (uint64_t)INT64_MAX) fail(2, "BAD_ARGUMENT");
  for (int i = 4; i < argc; i += 2) {
    if (!strcmp(argv[i], "--no-stdin-sha256")) { stdin_sha = 0; i--; continue; }  /* the caller hashes the source itself */
    if (i + 1 >= argc) fail(2, "BAD_ARGUMENT");
    if (!strcmp(argv[i], "--max-symbols") && parse_u64(argv[i + 1], &v) && v >= 1 && v <= FULL_MAX_CEILING) f_ceiling = (size_t)v;
    else if (!strcmp(argv[i], "--source-bytes") && parse_u64(argv[i + 1], &v)) { src_bytes = v; have_src_bytes = 1; }
    else if (!strcmp(argv[i], "--source-sha256") && hex64(argv[i + 1], src_sha)) have_src_sha = 1;
    else fail(2, "BAD_ARGUMENT");
  }
  T0 = (int64_t)t0; T1 = (int64_t)t1;
  fidx_cap = 8192; fidx = calloc(fidx_cap, sizeof *fidx); if (!fidx) fail(8, "OUT_OF_MEMORY");
  seg_fn = segment_all; hashing = stdin_sha; sha_init(&in_sha);
  int rc = read_capture();
  if (rc == 3) fail(3, "NO_CAPTURE_HEADER");
  if (rc == 4) fail(4, "BAD_PCAPNG_BLOCK");
  if (rc) return rc;                             /* 5: read_capture already named it */
  { unsigned char tail[1 << 16]; size_t got; while ((got = fread(tail, 1, sizeof tail, stdin)) > 0) { in_bytes += got; if (hashing) sha_update(&in_sha, tail, got); } }
  char sha[65]; sha_hex(&in_sha, sha);
  qsort(frecs, nfrec, sizeof *frecs, frec_cmp);
  static char obuf[1 << 20]; setvbuf(stdout, obuf, _IOFBF, sizeof obuf);
  uint64_t with_dir = 0, with_status = 0, with_round = 0, dir_only = 0;
  for (size_t i = 0; i < nfrec; i++) {
    FRec *r = &frecs[i];
    with_dir += r->dir_msgs > 0; with_status += r->status_msgs > 0; with_round += r->has_last;
    dir_only += r->dir_msgs > 0 && r->status_msgs == 0;
    fputs("{\"record\":\"symbol\",\"symbol\":", stdout); json_bytes(r->sym, 8);
    printf(",\"directory_seen\":%s,\"directory_messages\":%llu", B(r->dir_msgs), (unsigned long long)r->dir_msgs);
    if (r->dir_msgs) {
      printf(",\"directory_ts\":%llu,\"directory_flags\":%u,\"round_lot_size\":", (unsigned long long)r->dir_ts, r->dir_flags);
      if (r->has_round_lot) printf("%u", r->round_lot); else fputs("null", stdout);
    } else fputs(",\"directory_ts\":null,\"directory_flags\":null,\"round_lot_size\":null", stdout);
    printf(",\"trading_status_seen\":%s,\"status_messages\":%llu", B(r->status_msgs), (unsigned long long)r->status_msgs);
    if (r->status_msgs) {
      fputs(",\"trading_status\":", stdout); json_bytes(&r->status, 1);
      printf(",\"trading_status_ts\":%llu,\"trading_status_reason\":", (unsigned long long)r->status_ts); json_bytes(r->reason, 4);
    } else fputs(",\"trading_status\":null,\"trading_status_ts\":null,\"trading_status_reason\":null", stdout);
    if (r->has_last)
      printf(",\"last_round_trade\":{\"price_e4\":%lld,\"size\":%u,\"ts\":%llu,\"broken\":%s}", (long long)r->last_px, r->last_size,
             (unsigned long long)r->last_ts, B(r->last_broken));
    else fputs(",\"last_round_trade\":null", stdout);
    printf(",\"trade_reports\":%llu,\"trades_regular_round\":%llu,\"trades_regular_odd\":%llu,\"trades_excluded\":%llu"
           ",\"trade_breaks\":%llu,\"quote_updates\":%llu,\"other_messages\":%llu,\"messages\":%llu}\n",
           (unsigned long long)r->trade_reports, (unsigned long long)r->round_regular, (unsigned long long)r->odd_regular,
           (unsigned long long)r->excluded, (unsigned long long)r->breaks, (unsigned long long)r->quotes,
           (unsigned long long)r->other, (unsigned long long)r->msgs);
  }
  int gaps = seq_gaps > 0 || seq_regressions > 0;
  int complete = !in_truncated && !n_bad && !gaps && !n_caplen_short && n_segments > 0;
  printf("{\"record\":\"summary\",\"parser\":\"iex_last_trade\",\"parser_version\":\"" FULL_PARSER_VERSION "\",\"mode\":\"all_symbols\""
         ",\"symbol_ceiling\":%zu,\"symbols\":%zu,\"symbols_with_directory\":%llu,\"symbols_with_trading_status\":%llu"
         ",\"symbols_directory_without_status\":%llu,\"symbols_with_round_trade\":%llu"
         ",\"session_start_ns\":%llu,\"session_end_ns\":%llu,\"capture_format\":\"%s\",\"stdin_bytes\":%llu,\"stdin_sha256\":%s%s%s",
         f_ceiling, nfrec, (unsigned long long)with_dir, (unsigned long long)with_status, (unsigned long long)dir_only,
         (unsigned long long)with_round, (unsigned long long)t0, (unsigned long long)t1, capture_format,
         (unsigned long long)in_bytes, hashing ? "\"" : "", hashing ? sha : "null", hashing ? "\"" : "");
  if (have_src_bytes) printf(",\"source_bytes\":%llu", (unsigned long long)src_bytes); else fputs(",\"source_bytes\":null", stdout);
  if (have_src_sha) printf(",\"source_sha256\":\"%s\"", src_sha); else fputs(",\"source_sha256\":null", stdout);
  printf(",\"packets\":%llu,\"packets_caplen_short\":%llu,\"segments\":%llu,\"bad_segments\":%llu,\"messages\":%llu"
         ",\"symbol_messages\":%llu,\"short_symbol_messages\":%llu,\"directory_messages\":%llu,\"status_messages\":%llu"
         ",\"quote_updates\":%llu,\"trade_reports\":%llu,\"trade_breaks\":%llu"
         ",\"first_sequence\":%llu,\"sequence_gaps\":%llu,\"sequence_gap_messages\":%llu,\"sequence_regressions\":%llu,\"stream_changes\":%llu"
         ",\"truncated\":%s,\"symbol_ceiling_exceeded\":false,\"gaps_detected\":%s,\"complete\":%s}\n",
         (unsigned long long)n_packets, (unsigned long long)n_caplen_short, (unsigned long long)n_segments,
         (unsigned long long)n_bad, (unsigned long long)n_messages, (unsigned long long)f_symbol_msgs,
         (unsigned long long)f_short_symbol_msgs, (unsigned long long)f_dir, (unsigned long long)f_status,
         (unsigned long long)f_quotes, (unsigned long long)n_trades, (unsigned long long)f_breaks,
         (unsigned long long)seq_first, (unsigned long long)seq_gaps, (unsigned long long)seq_gap_msgs, (unsigned long long)seq_regressions,
         (unsigned long long)seq_stream_changes, B(in_truncated), B(gaps), B(complete));
  if (fflush(stdout) != 0) fail(9, "WRITE_FAILED");
  return 0;
}
