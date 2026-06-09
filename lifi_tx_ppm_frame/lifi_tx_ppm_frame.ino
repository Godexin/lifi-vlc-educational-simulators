#include <Arduino.h>
#include <string.h>
#include "soc/gpio_struct.h"
#include "soc/gpio_reg.h"

// ============================================================
//                      AYARLAR
// ============================================================

#define LED_PIN 18      // MOSFET gate / LED output. GPIO 0..31 olmalı.
#define VERBOSE_TX 1    // 1: detaylı frame çıktısı, 0: sadece istatistik

static const uint32_t Tslot_us  = 500;  // Her PPM alt-slot süresi
static const uint32_t Tpulse_us = 125;  // Pulse genişliği

static const size_t MAX_FRAME_BYTES = 64;
static const size_t MAX_BITS        = MAX_FRAME_BYTES * 8;
static const size_t MAX_PPM_SLOTS   = MAX_BITS / 2;

// ============================================================
//                      PROTOTİPLER
// ============================================================

void init_ppm_timers();
void start_ppm_tx(const uint8_t* slots, size_t nslots);
bool ppm_tx_busy();

// ============================================================
//                      FRAME SABİTLERİ
// ============================================================

// 0x1B preamble:
// 0x1B = 00011011
// 4-PPM mapping:
// 00 -> slot 0
// 01 -> slot 1
// 10 -> slot 2
// 11 -> slot 3
//
// Dolayısıyla 0x1B -> slot dizisi: 0,1,2,3
// PREAMBLE[4] -> 0,1,2,3, 0,1,2,3, 0,1,2,3, 0,1,2,3
static const uint8_t PREAMBLE_BYTE = 0x1B;
static const uint8_t PREAMBLE[4] = {
  PREAMBLE_BYTE,
  PREAMBLE_BYTE,
  PREAMBLE_BYTE,
  PREAMBLE_BYTE
};

// Sync word:
// 0xD3 = 11010011 -> slot 3,1,0,3
// 0x91 = 10010001 -> slot 2,1,0,1
static const uint8_t SYNCW[2] = {0xD3, 0x91};

// Type bitleri
static const uint8_t TYPE_DATA    = 1 << 0;
static const uint8_t TYPE_ACK_REQ = 1 << 1;

// TX için kalıcı slot buffer.
// ISR bu buffer'ı okuyacak.
static uint8_t tx_slots[MAX_PPM_SLOTS];
static size_t  tx_nslots = 0;

static uint8_t seq = 0;

// ============================================================
//                      TX İSTATİSTİKLERİ
// ============================================================

static uint32_t tx_frames_sent = 0;
static uint32_t last_tx_stats_ms = 0;

static void print_tx_stats_periodic() {
  uint32_t now = millis();

  if (now - last_tx_stats_ms < 5000) {
    return;
  }

  last_tx_stats_ms = now;

  Serial.println();
  Serial.println("========== TX STATS ==========");

  Serial.print("Frames sent: ");
  Serial.println(tx_frames_sent);

  Serial.print("Last seq   : ");
  Serial.println((uint8_t)(seq - 1));

  Serial.print("Tslot_us   : ");
  Serial.println(Tslot_us);

  Serial.print("Tpulse_us  : ");
  Serial.println(Tpulse_us);

  Serial.print("Last nslots: ");
  Serial.println(tx_nslots);

  Serial.println("==============================");
}

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
//                      BYTE / BIT DÖNÜŞÜMLERİ
// ============================================================

// bytes_to_bits: MSB-first
size_t bytes_to_bits(const uint8_t* in_bytes,
                     size_t in_len,
                     uint8_t* out_bits,
                     size_t out_max) {
  const size_t need = in_len * 8;
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

// 4-PPM mapping:
// 00 -> slot 0
// 01 -> slot 1
// 10 -> slot 2
// 11 -> slot 3
size_t bits_to_4ppm_slots(const uint8_t* bits,
                          size_t nbits,
                          uint8_t* out_slots,
                          size_t out_max_slots) {
  const size_t need_slots = (nbits + 1) / 2;

  if (out_max_slots < need_slots) return 0;

  size_t si = 0;

  for (size_t i = 0; i < nbits; i += 2) {
    uint8_t b0 = bits[i] & 0x01;
    uint8_t b1 = (i + 1 < nbits) ? (bits[i + 1] & 0x01) : 0;

    out_slots[si++] = (b0 << 1) | b1;
  }

  return si;
}

// Ters dönüşüm:
// slot 0 -> 00
// slot 1 -> 01
// slot 2 -> 10
// slot 3 -> 11
size_t slots_to_bits_4ppm(const uint8_t* slots,
                          size_t nslots,
                          uint8_t* out_bits,
                          size_t out_max_bits) {
  const size_t need_bits = nslots * 2;

  if (out_max_bits < need_bits) return 0;

  size_t bi = 0;

  for (size_t s = 0; s < nslots; s++) {
    uint8_t slot = slots[s] & 0x03;

    out_bits[bi++] = (slot >> 1) & 0x01;
    out_bits[bi++] = slot & 0x01;
  }

  return bi;
}

// bits[8] -> byte, MSB-first
uint8_t bits8_to_byte_msb(const uint8_t* bits8) {
  uint8_t b = 0;

  for (int i = 0; i < 8; i++) {
    b = (b << 1) | (bits8[i] & 0x01);
  }

  return b;
}

// ============================================================
//                      FRAME OLUŞTURMA
// ============================================================

static size_t build_frame_v1(uint8_t* out,
                             size_t out_max,
                             uint8_t type,
                             uint8_t seq_value,
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

  // Preamble
  memcpy(out + i, PREAMBLE, sizeof(PREAMBLE));
  i += sizeof(PREAMBLE);

  // Sync word
  memcpy(out + i, SYNCW, sizeof(SYNCW));
  i += sizeof(SYNCW);

  // Header başlangıcı
  const size_t hdr_start = i;

  out[i++] = 0x01;        // ver
  out[i++] = type;        // type
  out[i++] = seq_value;   // seq
  out[i++] = payload_len; // len
  out[i++] = 0x00;        // flags

  // Payload
  if (payload_len > 0 && payload != nullptr) {
    memcpy(out + i, payload, payload_len);
    i += payload_len;
  }

  // CRC hesaplama:
  // CRC = SYNCW + HEADER + PAYLOAD
  // Preamble CRC dışında.
  uint16_t crc = 0xFFFF;
  crc = crc16_ccitt(SYNCW, sizeof(SYNCW), crc);
  crc = crc16_ccitt(out + hdr_start, hdr_len, crc);

  if (payload_len > 0 && payload != nullptr) {
    crc = crc16_ccitt(payload, payload_len, crc);
  }

  // CRC low-byte first gönderiliyor.
  // RX tarafı aynı okumalı:
  // rx_crc = crc_low | (crc_high << 8)
  out[i++] = (uint8_t)(crc & 0xFF);
  out[i++] = (uint8_t)((crc >> 8) & 0xFF);

  return i;
}

// ============================================================
//                      DEBUG YARDIMCILARI
// ============================================================

static void print_hex(const uint8_t* data, size_t len) {
  for (size_t i = 0; i < len; i++) {
    if (data[i] < 16) Serial.print('0');

    Serial.print(data[i], HEX);
    Serial.print(i + 1 == len ? '\n' : ' ');
  }
}

static bool verify_byte_bit_roundtrip(const uint8_t* frame,
                                      size_t flen,
                                      const uint8_t* bits,
                                      size_t nbits) {
  if (nbits != flen * 8) {
#if VERBOSE_TX
    Serial.println("ERROR: nbits != flen*8");
    Serial.print("nbits=");
    Serial.print(nbits);
    Serial.print(" expected=");
    Serial.println(flen * 8);
#endif
    return false;
  }

  for (size_t bi = 0; bi < flen; bi++) {
    uint8_t rebuilt = bits8_to_byte_msb(&bits[bi * 8]);

    if (rebuilt != frame[bi]) {
#if VERBOSE_TX
      Serial.print("Round-trip FAIL at byte ");
      Serial.println(bi);

      Serial.print("orig=0x");
      Serial.print(frame[bi], HEX);

      Serial.print(" rebuilt=0x");
      Serial.println(rebuilt, HEX);
#endif
      return false;
    }
  }

  return true;
}

static bool verify_ppm_roundtrip(const uint8_t* bits,
                                 size_t nbits,
                                 const uint8_t* slots,
                                 size_t nslots) {
  uint8_t bits_back[MAX_BITS];

  size_t nbits_back = slots_to_bits_4ppm(slots,
                                         nslots,
                                         bits_back,
                                         sizeof(bits_back));

  if (nbits_back < nbits) {
#if VERBOSE_TX
    Serial.println("PPM round-trip FAIL: nbits_back < nbits");
#endif
    return false;
  }

  for (size_t i = 0; i < nbits; i++) {
    if ((bits_back[i] & 0x01) != (bits[i] & 0x01)) {
#if VERBOSE_TX
      Serial.print("PPM round-trip FAIL at bit ");
      Serial.println(i);
#endif
      return false;
    }
  }

  return true;
}

// ============================================================
//                      PPM TX - ESP32 TIMER
// ============================================================

hw_timer_t* timer_slot = nullptr;
hw_timer_t* timer_poff = nullptr;

// ISR ile ana kod arasında paylaşılan TX durumları
volatile const uint8_t* g_slots = nullptr;
volatile size_t g_nslots = 0;
volatile size_t g_slot_idx = 0;
volatile uint8_t g_subslot = 0;
volatile bool g_tx_active = false;

// GPIO hızlı sürme.
// Not: Bu yöntem GPIO 0..31 için geçerlidir.
static inline void IRAM_ATTR led_on_fast() {
  GPIO.out_w1ts = (1UL << LED_PIN);
}

static inline void IRAM_ATTR led_off_fast() {
  GPIO.out_w1tc = (1UL << LED_PIN);
}

// Pulse-off ISR:
// Pulse süresi dolunca LED kapanır.
void IRAM_ATTR onPulseOff() {
  led_off_fast();
  timerStop(timer_poff);
}

// Slot ISR:
// Her Tslot_us'te bir çalışır.
void IRAM_ATTR onSlotTick() {
  if (!g_tx_active || g_slots == nullptr || g_nslots == 0) {
    led_off_fast();
    return;
  }

  uint8_t pulse_slot = g_slots[g_slot_idx] & 0x03;

  if (g_subslot == pulse_slot) {
    led_on_fast();

    // Pulse-off timer init içinde ayarlandı.
    // ISR içinde timerAlarm() tekrar çağrılmıyor.
    timerStop(timer_poff);
    timerWrite(timer_poff, 0);
    timerStart(timer_poff);
  } else {
    led_off_fast();
  }

  g_subslot++;

  if (g_subslot >= 4) {
    g_subslot = 0;
    g_slot_idx++;

    if (g_slot_idx >= g_nslots) {
      g_tx_active = false;
      led_off_fast();
      timerStop(timer_slot);
    }
  }
}

bool ppm_tx_busy() {
  bool busy;

  noInterrupts();
  busy = g_tx_active;
  interrupts();

  return busy;
}

void start_ppm_tx(const uint8_t* slots, size_t nslots) {
  if (slots == nullptr || nslots == 0) return;

  noInterrupts();

  g_slots = slots;
  g_nslots = nslots;
  g_slot_idx = 0;
  g_subslot = 0;
  g_tx_active = true;

  interrupts();

  led_off_fast();

  timerStop(timer_slot);
  timerWrite(timer_slot, 0);
  timerStart(timer_slot);
}

void init_ppm_timers() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // ESP32 Arduino Core 3.x:
  // timerBegin(1000000) -> 1 MHz timer -> 1 tick = 1 us
  timer_slot = timerBegin(1000000);
  timerAttachInterrupt(timer_slot, &onSlotTick);
  timerWrite(timer_slot, 0);
  timerAlarm(timer_slot, Tslot_us, true, 0);
  timerStop(timer_slot);

  timer_poff = timerBegin(1000000);
  timerAttachInterrupt(timer_poff, &onPulseOff);
  timerWrite(timer_poff, 0);
  timerAlarm(timer_poff, Tpulse_us, false, 0);
  timerStop(timer_poff);
}

// ============================================================
//                      SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(200);

  Serial.println();
  Serial.println("TX frame + 4-PPM transmitter");
  Serial.println("Preamble: 0x1B 0x1B 0x1B 0x1B");
  Serial.println("Expected preamble slots: 0 1 2 3 repeated 4 times");
  Serial.println("CRC16-CCITT, MSB-first bits, 4-PPM slots");

  init_ppm_timers();

  // Basit byte-bit testi
  uint8_t test_bytes[1] = {0xA5};
  uint8_t test_bits[8];

  size_t tbits = bytes_to_bits(test_bytes, 1, test_bits, sizeof(test_bits));

  Serial.print("0xA5 bits: ");
  for (size_t i = 0; i < tbits; i++) {
    Serial.print(test_bits[i]);
  }
  Serial.println("  expected: 10100101");

  // 0x1B preamble slot testi
  uint8_t pre_bits[8];
  uint8_t pre_slots[4];

  bytes_to_bits(&PREAMBLE_BYTE, 1, pre_bits, sizeof(pre_bits));
  bits_to_4ppm_slots(pre_bits, 8, pre_slots, sizeof(pre_slots));

  Serial.print("0x1B slots: ");
  for (int i = 0; i < 4; i++) {
    Serial.print(pre_slots[i]);
    Serial.print(' ');
  }
  Serial.println(" expected: 0 1 2 3");
}

// ============================================================
//                      LOOP
// ============================================================

void loop() {
  // TX halen aktifse yeni frame hazırlayıp tx_slots buffer'ını bozma.
  if (ppm_tx_busy()) {
    return;
  }

  // Örnek payload
  uint8_t payload[4] = {
    0x00,
    0xF3,
    0x01,
    0x9A
  };

  uint8_t frame[MAX_FRAME_BYTES];

  uint8_t type = TYPE_DATA | TYPE_ACK_REQ;

  uint8_t seq_sent = seq;

  size_t flen = build_frame_v1(frame,
                               sizeof(frame),
                               type,
                               seq_sent,
                               payload,
                               sizeof(payload));

  seq++;

  if (flen == 0) {
    Serial.println("ERROR: frame buffer too small!");
    delay(1000);
    return;
  }

  uint8_t bits[MAX_BITS];

  size_t nbits = bytes_to_bits(frame,
                               flen,
                               bits,
                               sizeof(bits));

  if (nbits == 0) {
    Serial.println("ERROR: bits buffer too small!");
    delay(1000);
    return;
  }

  if (!verify_byte_bit_roundtrip(frame, flen, bits, nbits)) {
    Serial.println("Round-trip FAIL -> PPM slot uretilmiyor.");
    delay(1000);
    return;
  }

  uint8_t slots[MAX_PPM_SLOTS];

  size_t nslots = bits_to_4ppm_slots(bits,
                                     nbits,
                                     slots,
                                     sizeof(slots));

  if (nslots == 0) {
    Serial.println("ERROR: slots buffer too small!");
    delay(1000);
    return;
  }

  if (!verify_ppm_roundtrip(bits, nbits, slots, nslots)) {
    Serial.println("PPM round-trip FAIL -> TX baslatilmiyor.");
    delay(1000);
    return;
  }

#if VERBOSE_TX
  Serial.println();
  Serial.print("FRAME len=");
  Serial.println(flen);

  Serial.print("FRAME: ");
  print_hex(frame, flen);

  Serial.println("Round-trip OK");
  Serial.println("PPM round-trip OK");

  Serial.print("BITS count=");
  Serial.println(nbits);

  Serial.print("BITS first 32: ");
  for (int i = 0; i < 32 && i < (int)nbits; i++) {
    Serial.print(bits[i]);
  }
  Serial.println();

  Serial.print("SLOTS count=");
  Serial.println(nslots);

  Serial.print("SLOTS first 24: ");
  for (int i = 0; i < 24 && i < (int)nslots; i++) {
    Serial.print((int)slots[i]);
    Serial.print(' ');
  }
  Serial.println();

  // 0x1B preamble kullanıldığı için ilk 16 slot şu olmalı:
  // 0 1 2 3 0 1 2 3 0 1 2 3 0 1 2 3
  Serial.print("Expected first 16 preamble slots: ");
  Serial.println("0 1 2 3 0 1 2 3 0 1 2 3 0 1 2 3");
#endif

  // TX aktif değilken kalıcı TX buffer'ına kopyala.
  // Bu nokta kritik: ISR tx_slots okurken buraya girilmiyor.
  if (nslots > sizeof(tx_slots)) {
    Serial.println("ERROR: tx_slots buffer too small!");
    delay(1000);
    return;
  }

  memcpy(tx_slots, slots, nslots);
  tx_nslots = nslots;

  tx_frames_sent++;

#if VERBOSE_TX
  Serial.print("PPM TX start | seq=");
  Serial.print(seq_sent);
  Serial.print(" | sent=");
  Serial.println(tx_frames_sent);
#endif

  start_ppm_tx(tx_slots, tx_nslots);

  print_tx_stats_periodic();

  // Test için frame aralığı.
  // flen=17 byte -> 136 bit -> 68 sembol
  // 68 sembol * 4 slot * 500 us = 136 ms
  delay(1000);
}