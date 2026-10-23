/* IEX HIST (TOPS 1.6, IEX-TP v1) last regular-session trade per requested symbol, read from a decompressed pcap / pcap-ng
   stream on stdin. Usage: iex_last_trade <symbols-file> <session-start-ns> <session-end-ns>
   Output (stdout, consumed in memory by the caller, never logged): one line per requested symbol
     SYMBOL \t status \t price_e4 \t timestamp_ns \t regular_trades
   status: ROUND (last regular-session trade without the odd-lot flag), ODD_ONLY (only odd-lot trades in the session),
   NO_TRADE (no regular-session trade). Extended-hours flagged trades and trades outside [start, end) are ignored.
   Extra columns (listing diagnostics, no prices): security-directory seen 0/1, last trading status (T/H/P/O or -), trades
   in any session.
   A summary line "#STATS ..." goes to stderr (counts only). */
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
static void packet(const unsigned char *p, size_t len) {
  n_packets++;
  if (len < 14) return;
  size_t off = 12; uint16_t et = (uint16_t)(p[off] << 8 | p[off + 1]); off += 2;
  while (et == 0x8100 && len >= off + 4) { et = (uint16_t)(p[off + 2] << 8 | p[off + 3]); off += 4; }
  if (et != 0x0800 || len < off + 20) return;
  size_t ihl = (size_t)(p[off] & 0x0f) * 4; if (p[off + 9] != 17 || len < off + ihl + 8) return;
  off += ihl + 8;  /* UDP header */
  segment(p + off, len - off);
}

static unsigned char *buf; static size_t cap = 1 << 24;
static int readn(void *dst, size_t n) { return fread(dst, 1, n, stdin) == n; }

int main(int argc, char **argv) {
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
  static char iobuf[1 << 22]; setvbuf(stdin, iobuf, _IOFBF, sizeof iobuf);
  buf = malloc(cap);
  unsigned char hdr[24]; if (!readn(hdr, 4)) return 3;
  uint32_t magic = le32(hdr);
  if (magic == 0x0A0D0D0A) {  /* pcap-ng */
    uint32_t type = magic;
    for (;;) {
      unsigned char l4[4]; if (!readn(l4, 4)) break;
      uint32_t tl = le32(l4); if (tl < 12) return 4;
      size_t body = tl - 8; if (body > cap) { cap = body; buf = realloc(buf, cap); }
      if (!readn(buf, body)) break;
      if (type == 6 && body >= 24) { uint32_t caplen = le32(buf + 12); if (20 + (size_t)caplen <= body) packet(buf + 20, caplen); }
      else if (type == 3 && body >= 8) { uint32_t olen = le32(buf); packet(buf + 4, olen < body - 8 ? olen : body - 8); }
      unsigned char t4[4]; if (!readn(t4, 4)) break; type = le32(t4);
    }
  } else if (magic == 0xA1B2C3D4 || magic == 0xA1B23C4D) {  /* classic pcap, little endian */
    if (!readn(hdr + 4, 20)) return 3;
    unsigned char rh[16];
    while (readn(rh, 16)) {
      uint32_t incl = le32(rh + 8); if (incl > cap) { cap = incl; buf = realloc(buf, cap); }
      if (!readn(buf, incl)) break;
      packet(buf, incl);
    }
  } else { fprintf(stderr, "#ERROR unknown capture format\n"); return 5; }
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
