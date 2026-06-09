#include <Arduino.h>
#include <string.h>
#include "esp_timer.h"

/* =========================================================
   ===============  RX MODE SWITCH ==========================
   DONANIM YOKKEN:
      SIM_MODE = 1  -> Sahte PPM pulse üretir.
   DONANIM GELİNCE:
      SIM_MODE = 0  -> Gerçek RX_PIN interrupt ile çalışır.
   ========================================================= */
#define SIM_MODE 0
/* ========================================================= */

// ============================================================
//                      ZAMAN PARAMETRELERİ
// ============================================================

static const uint32_t Tslot_us  = 500;
static const uint32_t Tsym_us   = 4 * Tslot_us;   // 2000 us
static const uint32_t Tpulse_us = 125;

// ============================================================
//                      DONANIM AYARLARI
// ============================================================

#define RX_PIN 34

// Komparatör çıkışı ters ise RISING yerine FALLING yap.
#define RX_EDGE RISING

// ============================================================
//                      FRAME SABİTLERİ
// ============================================================

// TX ile aynı:
// 0x1B = 00011011
// 4-PPM slot karşılığı: 00 01 10 11 -> 0 1 2 3
static const uint8_t PREAMBLE_BYTE = 0x1B;
static const uint8_t PREAMBLE[4] = {
  PREAMBLE_BYTE,
  PREAMBLE_BYTE,
  PREAMBLE_BYTE,
  PREAMBLE_BYTE
};

// TX ile aynı sync word:
// 0xD3 -> slot 3,1,0,3
// 0x91 -> slot 2,1,0,1
static const uint8_t SYNCW[2] = {0xD3, 0x91};

struct FrameHeaderV1 {
  uint8_t ver;
  uint8_t type;
  uint8_t seq;
  uint8_t len;
  uint8_t flags;
} __attribute__((packed));

// ============================================================
//                      CRC16-CCITT
// ============================================================

static uint16_t crc16_ccitt(const uint8_t* data,
                            size_t len,
                            uint16_t crc = 0xFFFF) {
  while (len--) {
    crc ^= (uint16_t)(*data++) << 8;

    for (int i = 0; i < 8; i++) {
      if (crc & 0x8000) {
        crc = (crc << 1) ^ 0x1021;
      } else {
        crc = (crc << 1);
      }
    }
  }

  return crc;
}

// ============================================================
//                      RING BUFFER
// ============================================================

static const int RB_SIZE = 2048; // 2^n olmalı

volatile uint32_t rb[RB_SIZE];
volatile uint16_t rb_w = 0;
volatile uint16_t rb_r = 0;

portMUX_TYPE rbMux = portMUX_INITIALIZER_UNLOCKED;

static inline void rb_push_isr(uint32_t t) {
  uint16_t n = (rb_w + 1) & (RB_SIZE - 1);

  if (n != rb_r) {
    rb[rb_w] = t;
    rb_w = n;
  }
  // Overflow olursa pulse drop edilir.
}

static bool rb_pop(uint32_t &t) {
  bool ok = false;

  portENTER_CRITICAL(&rbMux);

  if (rb_r != rb_w) {
    t = rb[rb_r];
    rb_r = (rb_r + 1) & (RB_SIZE - 1);
    ok = true;
  }

  portEXIT_CRITICAL(&rbMux);

  return ok;
}

#if SIM_MODE == 0
void IRAM_ATTR onRxEdge() {
  uint32_t t = (uint32_t)esp_timer_get_time();

  portENTER_CRITICAL_ISR(&rbMux);
  rb_push_isr(t);
  portEXIT_CRITICAL_ISR(&rbMux);
}
#endif

// ============================================================
//                      RX DECODER STATE
// ============================================================

enum RxState {
  UNLOCKED,
  LOCKED
};

static RxState rx_state = UNLOCKED;

static uint32_t t_sym0 = 0;
static uint32_t sym_index = 0;

// 0x1B preamble 4 byte:
// 4 byte = 32 bit
// 4-PPM'de 2 bit = 1 sembol
// 32 bit / 2 = 16 sembol/pulse
static const uint8_t PREAMBLE_PULSES = 16;

// Preamble slot pattern:
// 0 1 2 3 repeated 4 times
static const uint8_t PREAMBLE_SLOT_PATTERN[PREAMBLE_PULSES] = {
  0, 1, 2, 3,
  0, 1, 2, 3,
  0, 1, 2, 3,
  0, 1, 2, 3
};

static uint32_t lock_ts[PREAMBLE_PULSES];
static uint8_t  lock_count = 0;

// Toleranslar
static const int32_t LOCK_TOL = 260;
static const int32_t WIN_TOL  = 260;

static inline int32_t iabs32(int32_t x) {
  return x < 0 ? -x : x;
}

// ============================================================
//                      SLOT -> BIT -> BYTE
// ============================================================

static inline void slot_to_2bits(uint8_t slot, uint8_t &b0, uint8_t &b1) {
  slot &= 0x03;

  b0 = (slot >> 1) & 0x01;
  b1 = slot & 0x01;
}

static uint8_t cur_byte = 0;
static uint8_t bit_cnt  = 0;

static uint8_t rx_bytes[2048];
static size_t  rx_nbytes = 0;

// ============================================================
//                      PDR / PER SAYAÇLARI
// ============================================================

static uint32_t frames_ok = 0;
static uint32_t crc_fail = 0;
static uint32_t missed_seq = 0;

static bool seq_started = false;
static uint8_t last_seq = 0;

static uint32_t last_stats_ms = 0;

static void update_seq_stats(uint8_t seq) {
  if (!seq_started) {
    seq_started = true;
    last_seq = seq;
    return;
  }

  uint8_t expected = last_seq + 1;

  if (seq != expected) {
    uint8_t missed = (uint8_t)(seq - expected);
    missed_seq += missed;
  }

  last_seq = seq;
}

static void print_stats_periodic() {
  uint32_t now = millis();

  if (now - last_stats_ms < 5000) {
    return;
  }

  last_stats_ms = now;

  uint32_t total_expected = frames_ok + crc_fail + missed_seq;

  Serial.println();
  Serial.println("========== RX STATS ==========");

  Serial.print("Frames OK     : ");
  Serial.println(frames_ok);

  Serial.print("CRC FAIL      : ");
  Serial.println(crc_fail);

  Serial.print("Missed SEQ    : ");
  Serial.println(missed_seq);

  Serial.print("Total expected: ");
  Serial.println(total_expected);

  if (total_expected > 0) {
    float pdr = 100.0f * (float)frames_ok / (float)total_expected;
    float per = 100.0f * (float)(crc_fail + missed_seq) / (float)total_expected;

    Serial.print("PDR           : ");
    Serial.print(pdr, 2);
    Serial.println(" %");

    Serial.print("PER           : ");
    Serial.print(per, 2);
    Serial.println(" %");
  }

  Serial.println("==============================");
}

static void reset_bitstream() {
  cur_byte = 0;
  bit_cnt = 0;
  rx_nbytes = 0;
}

static void push_bit(uint8_t bit) {
  cur_byte = (cur_byte << 1) | (bit & 0x01);
  bit_cnt++;

  if (bit_cnt == 8) {
    if (rx_nbytes < sizeof(rx_bytes)) {
      rx_bytes[rx_nbytes++] = cur_byte;
    } else {
      // Buffer dolarsa basit reset.
      rx_nbytes = 0;
    }

    cur_byte = 0;
    bit_cnt = 0;
  }
}

// ============================================================
//                      FRAME PARSER
// ============================================================

static void print_hex_line(const uint8_t* d, size_t n) {
  for (size_t i = 0; i < n; i++) {
    if (d[i] < 16) Serial.print('0');

    Serial.print(d[i], HEX);
    Serial.print(i + 1 == n ? '\n' : ' ');
  }
}

static bool try_parse_one_frame() {
  // Minimum:
  // PREAMBLE(4) + SYNC(2) + HEADER(5) + CRC(2) = 13 byte
  if (rx_nbytes < 13) return false;

  size_t i = 0;

  while (i + 13 <= rx_nbytes) {
    bool preamble_ok = memcmp(&rx_bytes[i], PREAMBLE, sizeof(PREAMBLE)) == 0;
    bool sync_ok     = memcmp(&rx_bytes[i + sizeof(PREAMBLE)],
                              SYNCW,
                              sizeof(SYNCW)) == 0;

    if (preamble_ok && sync_ok) {
      const size_t hdr_offset = i + sizeof(PREAMBLE) + sizeof(SYNCW);

      if (hdr_offset + sizeof(FrameHeaderV1) + 2 > rx_nbytes) {
        return false;
      }

      FrameHeaderV1 hdr;
      memcpy(&hdr, &rx_bytes[hdr_offset], sizeof(hdr));

      // Basit güvenlik kontrolleri
      if (hdr.ver != 0x01) {
        i++;
        continue;
      }

      if (hdr.len > 200) {
        i++;
        continue;
      }

      const size_t need = sizeof(PREAMBLE)
                        + sizeof(SYNCW)
                        + sizeof(FrameHeaderV1)
                        + hdr.len
                        + 2;

      if (i + need > rx_nbytes) {
        return false;
      }

      const uint8_t* payload = &rx_bytes[hdr_offset + sizeof(FrameHeaderV1)];

      // TX CRC low-byte-first gönderiyor.
      uint16_t crc_rx = (uint16_t)rx_bytes[i + need - 2] |
                        ((uint16_t)rx_bytes[i + need - 1] << 8);

      // CRC = SYNCW + HEADER + PAYLOAD
      uint16_t crc = 0xFFFF;
      crc = crc16_ccitt(SYNCW, sizeof(SYNCW), crc);
      crc = crc16_ccitt((const uint8_t*)&hdr, sizeof(hdr), crc);
      crc = crc16_ccitt(payload, hdr.len, crc);

      if (crc == crc_rx) {
        frames_ok++;
        update_seq_stats(hdr.seq);

        Serial.print("FRAME OK | ver=");
        Serial.print(hdr.ver);

        Serial.print(" type=");
        Serial.print(hdr.type);

        Serial.print(" seq=");
        Serial.print(hdr.seq);

        Serial.print(" len=");
        Serial.println(hdr.len);

        Serial.print("PAYLOAD: ");
        print_hex_line(payload, hdr.len);
      } else {
        crc_fail++;

        Serial.print("FRAME CRC FAIL | got=0x");
        Serial.print(crc_rx, HEX);

        Serial.print(" calc=0x");
        Serial.println(crc);
      }

      // Frame'i buffer'dan tüket.
      size_t remain = rx_nbytes - (i + need);
      memmove(rx_bytes, &rx_bytes[i + need], remain);
      rx_nbytes = remain;

      return true;
    }

    i++;
  }

  // Preamble bulunamadıysa buffer şişmesin.
  // Son 64 byte kalsın.
  if (rx_nbytes > 64) {
    memmove(rx_bytes, &rx_bytes[rx_nbytes - 64], 64);
    rx_nbytes = 64;
  }

  return false;
}

// ============================================================
//                      LOCK YARDIMCILARI
// ============================================================

static void reset_lock_buffer() {
  lock_count = 0;
}

static void add_lock_timestamp(uint32_t t) {
  if (lock_count < PREAMBLE_PULSES) {
    lock_ts[lock_count++] = t;
  } else {
    memmove(&lock_ts[0],
            &lock_ts[1],
            sizeof(lock_ts[0]) * (PREAMBLE_PULSES - 1));

    lock_ts[PREAMBLE_PULSES - 1] = t;
  }
}

static bool check_0x1B_preamble_lock(uint32_t &out_t_sym0) {
  if (lock_count < PREAMBLE_PULSES) return false;

  // Preamble'ın ilk sembolü slot 0'dır.
  // Yani ilk pulse yaklaşık sembol başlangıcında gelir.
  uint32_t candidate_t_sym0 = lock_ts[0];

  for (uint8_t i = 0; i < PREAMBLE_PULSES; i++) {
    uint8_t expected_slot = PREAMBLE_SLOT_PATTERN[i];

    uint32_t expected_t = candidate_t_sym0
                        + (uint32_t)i * Tsym_us
                        + (uint32_t)expected_slot * Tslot_us;

    int32_t err = (int32_t)(lock_ts[i] - expected_t);

    if (iabs32(err) > LOCK_TOL) {
      return false;
    }
  }

  out_t_sym0 = candidate_t_sym0;
  return true;
}

static void unlock_receiver(const char* reason) {
  rx_state = UNLOCKED;
  t_sym0 = 0;
  sym_index = 0;

  reset_bitstream();
  reset_lock_buffer();

  if (reason != nullptr) {
    Serial.print("UNLOCK: ");
    Serial.println(reason);
  }
}

// ============================================================
//                      LOCKED PULSE DECODER
// ============================================================

static bool decode_locked_pulse(uint32_t t, bool allow_unlock) {
  uint32_t t_sym_start = t_sym0 + sym_index * Tsym_us;
  int32_t off = (int32_t)(t - t_sym_start);

  // Geçerli slot merkezleri yaklaşık:
  // slot0: 0 us
  // slot1: 500 us
  // slot2: 1000 us
  // slot3: 1500 us
  //
  // 2000 us civarı artık bir sonraki semboldür, kabul etmiyoruz.
  if (off < -WIN_TOL || off > (int32_t)(3 * Tslot_us + WIN_TOL)) {
    if (allow_unlock) {
      unlock_receiver("timing out of symbol window");

      // Bu pulse yeni frame'in ilk preamble pulse'ı olabilir.
      add_lock_timestamp(t);
    }

    return false;
  }

  int slot = (off + (int32_t)Tslot_us / 2) / (int32_t)Tslot_us;

  if (slot < 0 || slot > 3) {
    if (allow_unlock) {
      unlock_receiver("invalid slot");

      // Bu pulse yeni frame'in ilk preamble pulse'ı olabilir.
      add_lock_timestamp(t);
    }

    return false;
  }

  uint8_t b0, b1;
  slot_to_2bits((uint8_t)slot, b0, b1);

  push_bit(b0);
  push_bit(b1);

  sym_index++;

  while (try_parse_one_frame()) {}

  return true;
}

// ============================================================
//                      PULSE İŞLEME
// ============================================================

static void process_pulse_timestamp(uint32_t t) {
  if (rx_state == UNLOCKED) {
    add_lock_timestamp(t);

    uint32_t candidate_t_sym0 = 0;

    if (check_0x1B_preamble_lock(candidate_t_sym0)) {
      rx_state = LOCKED;
      t_sym0 = candidate_t_sym0;
      sym_index = 0;

      reset_bitstream();

      Serial.println("LOCKED | preamble 0x1B pattern detected");
      Serial.println("Expected preamble slots: 0 1 2 3 repeated 4 times");

      // Kritik nokta:
      // Lock için topladığımız 16 preamble pulse'ını tekrar decode ediyoruz.
      // Böylece byte stream'in başında tam 0x1B 0x1B 0x1B 0x1B oluşuyor.
      for (uint8_t i = 0; i < PREAMBLE_PULSES; i++) {
        decode_locked_pulse(lock_ts[i], false);
      }

      reset_lock_buffer();
    }

    return;
  }

  // LOCKED durumunda normal pulse decode edilir.
  decode_locked_pulse(t, true);
}

// ============================================================
//                      SIM MODE
// ============================================================

#if SIM_MODE == 1

static size_t build_frame_v1(uint8_t* out,
                             size_t out_max,
                             uint8_t type,
                             uint8_t seq,
                             const uint8_t* payload,
                             uint8_t payload_len) {
  const size_t hdr_len = 5;
  const size_t need = sizeof(PREAMBLE)
                    + sizeof(SYNCW)
                    + hdr_len
                    + payload_len
                    + 2;

  if (out_max < need) return 0;

  size_t i = 0;

  memcpy(out + i, PREAMBLE, sizeof(PREAMBLE));
  i += sizeof(PREAMBLE);

  memcpy(out + i, SYNCW, sizeof(SYNCW));
  i += sizeof(SYNCW);

  const size_t hdr_start = i;

  out[i++] = 0x01;
  out[i++] = type;
  out[i++] = seq;
  out[i++] = payload_len;
  out[i++] = 0x00;

  if (payload_len > 0 && payload != nullptr) {
    memcpy(out + i, payload, payload_len);
    i += payload_len;
  }

  uint16_t crc = 0xFFFF;
  crc = crc16_ccitt(SYNCW, sizeof(SYNCW), crc);
  crc = crc16_ccitt(out + hdr_start, hdr_len, crc);

  if (payload_len > 0 && payload != nullptr) {
    crc = crc16_ccitt(payload, payload_len, crc);
  }

  // TX ile aynı: CRC low-byte-first
  out[i++] = (uint8_t)(crc & 0xFF);
  out[i++] = (uint8_t)((crc >> 8) & 0xFF);

  return i;
}

static size_t bytes_to_bits(const uint8_t* in_bytes,
                            size_t in_len,
                            uint8_t* out_bits,
                            size_t out_max) {
  size_t need = in_len * 8;

  if (out_max < need) return 0;

  size_t k = 0;

  for (size_t i = 0; i < in_len; i++) {
    uint8_t b = in_bytes[i];

    for (int bit = 7; bit >= 0; bit--) {
      out_bits[k++] = (b >> bit) & 0x01;
    }
  }

  return k;
}

static size_t bits_to_4ppm_slots(const uint8_t* bits,
                                 size_t nbits,
                                 uint8_t* out_slots,
                                 size_t out_max_slots) {
  size_t need_slots = (nbits + 1) / 2;

  if (out_max_slots < need_slots) return 0;

  size_t si = 0;

  for (size_t i = 0; i < nbits; i += 2) {
    uint8_t b0 = bits[i] & 0x01;
    uint8_t b1 = (i + 1 < nbits) ? (bits[i + 1] & 0x01) : 0;

    out_slots[si++] = (b0 << 1) | b1;
  }

  return si;
}

static uint32_t sim_t = 100000;
static uint8_t  sim_seq = 0;

static void sim_emit_frame_as_pulses() {
  uint8_t payload[4] = {
    0x00,
    0xF3,
    0x01,
    0x9A
  };

  uint8_t frame[128];

  uint8_t type = 0;
  type |= 1;
  type |= (1 << 1);

  size_t flen = build_frame_v1(frame,
                               sizeof(frame),
                               type,
                               sim_seq++,
                               payload,
                               sizeof(payload));

  if (!flen) return;

  uint8_t bits[1024];

  size_t nbits = bytes_to_bits(frame,
                               flen,
                               bits,
                               sizeof(bits));

  if (!nbits) return;

  uint8_t slots[512];

  size_t nslots = bits_to_4ppm_slots(bits,
                                     nbits,
                                     slots,
                                     sizeof(slots));

  if (!nslots) return;

  Serial.print("SIM FRAME seq=");
  Serial.print(sim_seq - 1);
  Serial.print(" slots first 16: ");

  for (int i = 0; i < 16 && i < (int)nslots; i++) {
    Serial.print((int)slots[i]);
    Serial.print(' ');
  }

  Serial.println();

  for (size_t s = 0; s < nslots; s++) {
    uint8_t slot = slots[s] & 0x03;

    uint32_t t_pulse = sim_t + (uint32_t)slot * Tslot_us;

    // SIM_MODE'da normal context; interrupt yok.
    rb_push_isr(t_pulse);

    sim_t += Tsym_us;
  }

  // Frame'ler arası boşluk.
  sim_t += 200000;
}

#endif

// ============================================================
//                      SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(200);

  Serial.println();
  Serial.println("RX FULL MODE");
  Serial.println("Preamble: 0x1B 0x1B 0x1B 0x1B");
  Serial.println("Preamble slots: 0 1 2 3 repeated 4 times");
  Serial.println("Sync: 0xD3 0x91");
  Serial.println("CRC16-CCITT, CRC low-byte-first");

#if SIM_MODE == 1
  Serial.println("SIM_MODE=1 | generating TX-like frames and decoding them");
#else
  Serial.println("SIM_MODE=0 | waiting pulses on RX_PIN");
  pinMode(RX_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(RX_PIN), onRxEdge, RX_EDGE);
#endif
}

// ============================================================
//                      LOOP
// ============================================================

void loop() {
#if SIM_MODE == 1
  sim_emit_frame_as_pulses();
  delay(20);
#endif

  uint32_t t;

  while (rb_pop(t)) {
    process_pulse_timestamp(t);
  }

  print_stats_periodic();

  delay(2);
}