// SPDX-License-Identifier: LicenseRef-AnoPKI-Enterprise
#include "pki.hpp"

#include <anocrypto/anocrypto.h>

#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace anopki::crypto::enterprise::pki {
namespace {

using Bytes = std::vector<std::uint8_t>;

constexpr std::size_t kMaxInput = 1024U * 1024U;
constexpr std::size_t kMaxKeyInput = 64U * 1024U;
constexpr std::size_t kMaxDepth = 32U;
constexpr std::size_t kMaxCollection = 1024U;

constexpr std::string_view kOidRsaEncryption = "1.2.840.113549.1.1.1";
constexpr std::string_view kOidSha256WithRsa = "1.2.840.113549.1.1.11";
constexpr std::string_view kOidSha384WithRsa = "1.2.840.113549.1.1.12";
constexpr std::string_view kOidSha512WithRsa = "1.2.840.113549.1.1.13";
constexpr std::string_view kOidEcPublicKey = "1.2.840.10045.2.1";
constexpr std::string_view kOidP256 = "1.2.840.10045.3.1.7";
constexpr std::string_view kOidEcdsaSha256 = "1.2.840.10045.4.3.2";
constexpr std::string_view kOidExtensionRequest = "1.2.840.113549.1.9.14";
constexpr std::string_view kOidSubjectAltName = "2.5.29.17";
constexpr std::string_view kOidBasicConstraints = "2.5.29.19";
constexpr std::string_view kOidKeyUsage = "2.5.29.15";
constexpr std::string_view kOidExtendedKeyUsage = "2.5.29.37";
constexpr std::string_view kOidSubjectKeyIdentifier = "2.5.29.14";
constexpr std::string_view kOidAuthorityKeyIdentifier = "2.5.29.35";
constexpr std::string_view kOidNameConstraints = "2.5.29.30";
constexpr std::string_view kOidAuthorityInfoAccess = "1.3.6.1.5.5.7.1.1";
constexpr std::string_view kOidCaIssuers = "1.3.6.1.5.5.7.48.2";
constexpr std::string_view kOidCrlDistributionPoints = "2.5.29.31";
constexpr std::string_view kOidCrlNumber = "2.5.29.20";
constexpr std::string_view kOidCrlReason = "2.5.29.21";
constexpr std::string_view kOidOcspSigning = "1.3.6.1.5.5.7.3.9";
constexpr std::string_view kOidOcspNonce = "1.3.6.1.5.5.7.48.1.2";
constexpr std::string_view kOidOcspBasic = "1.3.6.1.5.5.7.48.1.1";
constexpr std::string_view kOidSha1 = "1.3.14.3.2.26";
constexpr std::string_view kOidSha256 = "2.16.840.1.101.3.4.2.1";
constexpr std::string_view kOidSha384 = "2.16.840.1.101.3.4.2.2";
constexpr std::string_view kOidSha512 = "2.16.840.1.101.3.4.2.3";

class CodecError : public std::runtime_error {
public:
    CodecError() : std::runtime_error{"codec.invalid"} {}
};

class UnsupportedAlgorithm final : public CodecError {};

[[noreturn]] void codec_fail() { throw CodecError{}; }
[[noreturn]] void unsupported_algorithm() { throw UnsupportedAlgorithm{}; }
[[noreturn]] void fail(std::string_view code) { throw std::runtime_error{std::string{code}}; }

void require_size(std::size_t size, std::size_t limit = kMaxInput)
{
    if (size == 0 || size > limit) codec_fail();
}

void append(Bytes &target, const Bytes &value) { target.insert(target.end(), value.begin(), value.end()); }
void append(Bytes &target, std::string_view value)
{
    target.insert(target.end(), reinterpret_cast<const std::uint8_t *>(value.data()),
                  reinterpret_cast<const std::uint8_t *>(value.data()) + value.size());
}

std::string_view view(const Bytes &value)
{
    return {reinterpret_cast<const char *>(value.data()), value.size()};
}

Bytes bytes(std::string_view value)
{
    return {reinterpret_cast<const std::uint8_t *>(value.data()),
            reinterpret_cast<const std::uint8_t *>(value.data()) + value.size()};
}

struct Node {
    std::uint8_t tag{};
    std::string_view encoded;
    std::string_view content;
};

class Reader {
public:
    explicit Reader(std::string_view input, std::size_t depth = 0) : input_{input}, depth_{depth}
    {
        if (depth_ > kMaxDepth) codec_fail();
    }

    [[nodiscard]] bool empty() const noexcept { return offset_ == input_.size(); }
    [[nodiscard]] std::uint8_t peek() const
    {
        if (empty()) codec_fail();
        return static_cast<std::uint8_t>(input_[offset_]);
    }
    [[nodiscard]] std::size_t depth() const noexcept { return depth_; }

    Node read()
    {
        if (empty() || ++count_ > kMaxCollection) codec_fail();
        const std::size_t start = offset_;
        const std::uint8_t tag = static_cast<std::uint8_t>(input_[offset_++]);
        if ((tag & 0x1fU) == 0x1fU || offset_ >= input_.size()) codec_fail();
        std::size_t length = static_cast<std::uint8_t>(input_[offset_++]);
        if ((length & 0x80U) != 0U)
        {
            const std::size_t octets = length & 0x7fU;
            if (octets == 0 || octets > sizeof(std::size_t) || octets > 4 ||
                offset_ + octets > input_.size() || static_cast<std::uint8_t>(input_[offset_]) == 0)
                codec_fail();
            length = 0;
            for (std::size_t index = 0; index < octets; ++index)
            {
                length = (length << 8U) | static_cast<std::uint8_t>(input_[offset_++]);
            }
            if (length < 128U) codec_fail();
        }
        if (length > kMaxInput || offset_ + length > input_.size()) codec_fail();
        const std::size_t content_offset = offset_;
        offset_ += length;
        return Node{tag, input_.substr(start, offset_ - start), input_.substr(content_offset, length)};
    }

    Node read(std::uint8_t expected)
    {
        Node result = read();
        if (result.tag != expected) codec_fail();
        return result;
    }

    void finish() const { if (!empty()) codec_fail(); }

private:
    std::string_view input_;
    std::size_t depth_{};
    std::size_t offset_{};
    std::size_t count_{};
};

Reader child(const Reader &parent, const Node &node) { return Reader{node.content, parent.depth() + 1U}; }

Bytes tlv(std::uint8_t tag, const Bytes &content)
{
    if (content.size() > kMaxInput) codec_fail();
    Bytes result{tag};
    if (content.size() < 128U)
    {
        result.push_back(static_cast<std::uint8_t>(content.size()));
    }
    else
    {
        std::array<std::uint8_t, sizeof(std::size_t)> encoded{};
        std::size_t value = content.size();
        std::size_t count = 0;
        while (value != 0)
        {
            encoded[encoded.size() - 1U - count++] = static_cast<std::uint8_t>(value & 0xffU);
            value >>= 8U;
        }
        result.push_back(static_cast<std::uint8_t>(0x80U | count));
        result.insert(result.end(), encoded.end() - static_cast<std::ptrdiff_t>(count), encoded.end());
    }
    append(result, content);
    return result;
}

Bytes join(std::initializer_list<Bytes> values)
{
    Bytes result;
    for (const Bytes &value : values) append(result, value);
    return result;
}

Bytes sequence(const Bytes &content) { return tlv(0x30, content); }
Bytes sequence(std::initializer_list<Bytes> values) { return sequence(join(values)); }
Bytes set_of(const Bytes &content) { return tlv(0x31, content); }
Bytes octet_string(const Bytes &value) { return tlv(0x04, value); }
Bytes null_value() { return tlv(0x05, {}); }
Bytes boolean(bool value) { return tlv(0x01, Bytes{static_cast<std::uint8_t>(value ? 0xff : 0x00)}); }

Bytes base128(std::uint64_t value)
{
    std::array<std::uint8_t, 10> reversed{};
    std::size_t count = 0;
    do
    {
        reversed[count++] = static_cast<std::uint8_t>(value & 0x7fU);
        value >>= 7U;
    } while (value != 0);
    Bytes result;
    while (count != 0)
    {
        const std::uint8_t part = reversed[--count];
        result.push_back(static_cast<std::uint8_t>(part | (count == 0 ? 0 : 0x80)));
    }
    return result;
}

std::vector<std::uint64_t> oid_arcs(std::string_view text)
{
    std::vector<std::uint64_t> arcs;
    while (!text.empty())
    {
        const std::size_t dot = text.find('.');
        const std::string_view part = text.substr(0, dot);
        if (part.empty() || (part.size() > 1 && part.front() == '0')) codec_fail();
        std::uint64_t value{};
        const auto [end, error] = std::from_chars(part.data(), part.data() + part.size(), value);
        if (error != std::errc{} || end != part.data() + part.size()) codec_fail();
        arcs.push_back(value);
        if (dot == std::string_view::npos) break;
        text.remove_prefix(dot + 1U);
    }
    if (arcs.size() < 2 || arcs[0] > 2 || (arcs[0] < 2 && arcs[1] > 39)) codec_fail();
    return arcs;
}

Bytes oid(std::string_view text)
{
    const auto arcs = oid_arcs(text);
    Bytes content = base128(arcs[0] * 40U + arcs[1]);
    for (std::size_t index = 2; index < arcs.size(); ++index) append(content, base128(arcs[index]));
    return tlv(0x06, content);
}

std::string decode_oid(const Node &node)
{
    if (node.tag != 0x06 || node.content.empty()) codec_fail();
    std::vector<std::uint64_t> values;
    std::uint64_t value = 0;
    bool first_octet = true;
    for (const unsigned char byte : node.content)
    {
        if (first_octet && byte == 0x80) codec_fail();
        first_octet = false;
        if (value > (UINT64_MAX >> 7U)) codec_fail();
        value = (value << 7U) | (byte & 0x7fU);
        if ((byte & 0x80U) == 0)
        {
            values.push_back(value);
            value = 0;
            first_octet = true;
        }
    }
    if (!first_octet || values.empty()) codec_fail();
    const std::uint64_t combined = values.front();
    const std::uint64_t first = combined < 40 ? 0 : combined < 80 ? 1 : 2;
    const std::uint64_t second = combined - first * 40;
    std::string result = std::to_string(first) + "." + std::to_string(second);
    for (std::size_t index = 1; index < values.size(); ++index) result += "." + std::to_string(values[index]);
    return result;
}

Bytes canonical_unsigned(std::string_view content, bool allow_zero = true)
{
    if (content.empty() || (static_cast<unsigned char>(content.front()) & 0x80U) != 0) codec_fail();
    if (content.size() > 1 && content.front() == '\0' &&
        (static_cast<unsigned char>(content[1]) & 0x80U) == 0) codec_fail();
    if (!allow_zero && content.size() == 1 && content.front() == '\0') codec_fail();
    if (content.size() > 1 && content.front() == '\0') content.remove_prefix(1);
    return bytes(content);
}

Bytes positive_integer(const Node &node, bool allow_zero = true)
{
    if (node.tag != 0x02) codec_fail();
    return canonical_unsigned(node.content, allow_zero);
}

Bytes integer(const Bytes &unsigned_value)
{
    if (unsigned_value.empty()) return tlv(0x02, Bytes{0});
    std::size_t first = 0;
    while (first + 1U < unsigned_value.size() && unsigned_value[first] == 0) ++first;
    Bytes content(unsigned_value.begin() + static_cast<std::ptrdiff_t>(first), unsigned_value.end());
    if ((content.front() & 0x80U) != 0) content.insert(content.begin(), 0);
    return tlv(0x02, content);
}

Bytes integer(std::uint64_t value)
{
    Bytes content;
    do
    {
        content.insert(content.begin(), static_cast<std::uint8_t>(value & 0xffU));
        value >>= 8U;
    } while (value != 0);
    return integer(content);
}

Bytes decimal_bytes(std::string_view decimal)
{
    if (decimal.empty()) codec_fail();
    Bytes result{0};
    for (const unsigned char ch : decimal)
    {
        if (!std::isdigit(ch)) codec_fail();
        unsigned carry = ch - '0';
        for (std::size_t index = result.size(); index-- > 0;)
        {
            const unsigned value = result[index] * 10U + carry;
            result[index] = static_cast<std::uint8_t>(value & 0xffU);
            carry = value >> 8U;
        }
        if (carry != 0) result.insert(result.begin(), static_cast<std::uint8_t>(carry));
        if (result.size() > 256U) codec_fail();
    }
    while (result.size() > 1 && result.front() == 0) result.erase(result.begin());
    return result;
}

std::string decimal_string(Bytes value)
{
    if (value.empty()) codec_fail();
    std::string result;
    while (!(value.size() == 1 && value.front() == 0))
    {
        unsigned remainder = 0;
        for (std::uint8_t &byte : value)
        {
            const unsigned current = (remainder << 8U) | byte;
            byte = static_cast<std::uint8_t>(current / 10U);
            remainder = current % 10U;
        }
        result.push_back(static_cast<char>('0' + remainder));
        while (value.size() > 1 && value.front() == 0) value.erase(value.begin());
    }
    if (result.empty()) return "0";
    std::reverse(result.begin(), result.end());
    return result;
}

Bytes padded(Bytes value, std::size_t size)
{
    if (value.size() > size) codec_fail();
    value.insert(value.begin(), size - value.size(), 0);
    return value;
}

std::string hex(const Bytes &value)
{
    std::ostringstream output;
    output << std::hex << std::setfill('0');
    for (const std::uint8_t byte : value) output << std::setw(2) << static_cast<unsigned>(byte);
    return output.str();
}

Bytes unhex(std::string_view value)
{
    if (value.size() % 2 != 0 || value.size() > kMaxInput * 2U) codec_fail();
    Bytes result;
    result.reserve(value.size() / 2U);
    for (std::size_t index = 0; index < value.size(); index += 2U)
    {
        unsigned parsed{};
        const auto [end, error] = std::from_chars(value.data() + index, value.data() + index + 2U, parsed, 16);
        if (error != std::errc{} || end != value.data() + index + 2U) codec_fail();
        result.push_back(static_cast<std::uint8_t>(parsed));
    }
    return result;
}

int base64_value(unsigned char ch)
{
    if (ch >= 'A' && ch <= 'Z') return ch - 'A';
    if (ch >= 'a' && ch <= 'z') return ch - 'a' + 26;
    if (ch >= '0' && ch <= '9') return ch - '0' + 52;
    if (ch == '+') return 62;
    if (ch == '/') return 63;
    return -1;
}

Bytes decode_base64(std::string_view input)
{
    if (input.empty() || input.size() % 4U != 0) codec_fail();
    Bytes result;
    result.reserve(input.size() / 4U * 3U);
    for (std::size_t index = 0; index < input.size(); index += 4U)
    {
        const bool final = index + 4U == input.size();
        const int a = base64_value(static_cast<unsigned char>(input[index]));
        const int b = base64_value(static_cast<unsigned char>(input[index + 1U]));
        const int c = input[index + 2U] == '=' ? -2 : base64_value(static_cast<unsigned char>(input[index + 2U]));
        const int d = input[index + 3U] == '=' ? -2 : base64_value(static_cast<unsigned char>(input[index + 3U]));
        if (a < 0 || b < 0 || c == -1 || d == -1 || (!final && (c < 0 || d < 0)) ||
            (c == -2 && d != -2) || (c == -2 && (b & 0x0f) != 0) ||
            (d == -2 && c >= 0 && (c & 0x03) != 0))
            codec_fail();
        result.push_back(static_cast<std::uint8_t>((a << 2U) | (b >> 4U)));
        if (c >= 0)
        {
            result.push_back(static_cast<std::uint8_t>((b << 4U) | (c >> 2U)));
            if (d >= 0) result.push_back(static_cast<std::uint8_t>((c << 6U) | d));
        }
    }
    require_size(result.size());
    return result;
}

std::string encode_base64(const Bytes &input)
{
    constexpr char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string result;
    for (std::size_t index = 0; index < input.size(); index += 3U)
    {
        const std::uint32_t a = input[index];
        const std::uint32_t b = index + 1U < input.size() ? input[index + 1U] : 0;
        const std::uint32_t c = index + 2U < input.size() ? input[index + 2U] : 0;
        result.push_back(alphabet[a >> 2U]);
        result.push_back(alphabet[((a & 3U) << 4U) | (b >> 4U)]);
        result.push_back(index + 1U < input.size() ? alphabet[((b & 15U) << 2U) | (c >> 6U)] : '=');
        result.push_back(index + 2U < input.size() ? alphabet[c & 63U] : '=');
    }
    return result;
}

struct PemBlock { std::string label; Bytes der; };

PemBlock decode_pem(std::string_view pem, const std::set<std::string> &allowed, std::size_t limit = kMaxInput)
{
    require_size(pem.size(), limit);
    if (pem.find('\0') != std::string_view::npos) codec_fail();
    std::string normalized;
    normalized.reserve(pem.size());
    for (std::size_t index = 0; index < pem.size(); ++index)
    {
        if (pem[index] == '\r')
        {
            if (index + 1U >= pem.size() || pem[index + 1U] != '\n') codec_fail();
            continue;
        }
        normalized.push_back(pem[index]);
    }
    while (!normalized.empty() && normalized.back() == '\n') normalized.pop_back();
    constexpr std::string_view prefix = "-----BEGIN ";
    if (!normalized.starts_with(prefix)) codec_fail();
    const std::size_t begin_end = normalized.find("-----\n");
    if (begin_end == std::string::npos) codec_fail();
    const std::string label = normalized.substr(prefix.size(), begin_end - prefix.size());
    if (!allowed.contains(label)) codec_fail();
    const std::string footer = "-----END " + label + "-----";
    const std::size_t footer_pos = normalized.rfind(footer);
    if (footer_pos == std::string::npos || footer_pos + footer.size() != normalized.size()) codec_fail();
    std::string encoded;
    std::size_t position = begin_end + 6U;
    while (position < footer_pos)
    {
        const std::size_t newline = normalized.find('\n', position);
        const std::size_t end = newline == std::string::npos ? footer_pos : std::min(newline, footer_pos);
        const std::string_view line{normalized.data() + position, end - position};
        if (line.empty() || line.size() > 64U) codec_fail();
        encoded.append(line);
        position = end + 1U;
    }
    if (position != footer_pos) codec_fail();
    return {label, decode_base64(encoded)};
}

std::string encode_pem(std::string_view label, const Bytes &der)
{
    const std::string encoded = encode_base64(der);
    std::string result = "-----BEGIN " + std::string{label} + "-----\n";
    for (std::size_t offset = 0; offset < encoded.size(); offset += 64U)
        result.append(encoded.substr(offset, 64U)).push_back('\n');
    result += "-----END " + std::string{label} + "-----\n";
    return result;
}

struct DateTime {
    int year{}, month{}, day{}, hour{}, minute{}, second{};
};

bool leap(int year) { return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0); }
int month_days(int year, int month)
{
    constexpr int days[] = {0,31,28,31,30,31,30,31,31,30,31,30,31};
    if (month < 1 || month > 12) codec_fail();
    return month == 2 && leap(year) ? 29 : days[month];
}

int digits(std::string_view value, std::size_t offset, std::size_t count)
{
    if (offset + count > value.size()) codec_fail();
    int result = 0;
    for (std::size_t index = 0; index < count; ++index)
    {
        const unsigned char ch = value[offset + index];
        if (!std::isdigit(ch)) codec_fail();
        result = result * 10 + ch - '0';
    }
    return result;
}

void validate(const DateTime &value)
{
    if (value.year < 1950 || value.year > 9999 || value.month < 1 || value.month > 12 ||
        value.day < 1 || value.day > month_days(value.year, value.month) || value.hour < 0 || value.hour > 23 ||
        value.minute < 0 || value.minute > 59 || value.second < 0 || value.second > 59) codec_fail();
}

std::int64_t days_from_civil(int year, unsigned month, unsigned day)
{
    year -= month <= 2;
    const int era = (year >= 0 ? year : year - 399) / 400;
    const unsigned yoe = static_cast<unsigned>(year - era * 400);
    const unsigned adjusted_month = static_cast<unsigned>(static_cast<int>(month) + (month > 2 ? -3 : 9));
    const unsigned doy = (153U * adjusted_month + 2U) / 5U + day - 1U;
    const unsigned doe = yoe * 365U + yoe / 4U - yoe / 100U + doy;
    return static_cast<std::int64_t>(era) * 146097 + doe - 719468;
}

DateTime civil_from_days(std::int64_t days)
{
    days += 719468;
    const std::int64_t era = (days >= 0 ? days : days - 146096) / 146097;
    const unsigned doe = static_cast<unsigned>(days - era * 146097);
    const unsigned yoe = (doe - doe / 1460U + doe / 36524U - doe / 146096U) / 365U;
    int year = static_cast<int>(yoe) + static_cast<int>(era) * 400;
    const unsigned doy = doe - (365U * yoe + yoe / 4U - yoe / 100U);
    const unsigned mp = (5U * doy + 2U) / 153U;
    const unsigned day = doy - (153U * mp + 2U) / 5U + 1U;
    const unsigned month = static_cast<unsigned>(static_cast<int>(mp) + (mp < 10 ? 3 : -9));
    year += month <= 2;
    return {year, static_cast<int>(month), static_cast<int>(day), 0, 0, 0};
}

std::int64_t epoch(const DateTime &value)
{
    validate(value);
    return days_from_civil(value.year, value.month, value.day) * 86400 + value.hour * 3600 + value.minute * 60 + value.second;
}

DateTime from_epoch(std::int64_t seconds)
{
    std::int64_t days = seconds / 86400;
    std::int64_t rest = seconds % 86400;
    if (rest < 0) { rest += 86400; --days; }
    DateTime result = civil_from_days(days);
    result.hour = static_cast<int>(rest / 3600);
    result.minute = static_cast<int>((rest % 3600) / 60);
    result.second = static_cast<int>(rest % 60);
    validate(result);
    return result;
}

std::string rfc3339(const DateTime &value)
{
    validate(value);
    std::ostringstream out;
    out << std::setfill('0') << std::setw(4) << value.year << '-' << std::setw(2) << value.month << '-'
        << std::setw(2) << value.day << 'T' << std::setw(2) << value.hour << ':' << std::setw(2) << value.minute
        << ':' << std::setw(2) << value.second << 'Z';
    return out.str();
}

DateTime parse_rfc3339(std::string_view value)
{
    if (value.size() < 20 || value[4] != '-' || value[7] != '-' || value[10] != 'T' || value[13] != ':' || value[16] != ':') codec_fail();
    DateTime local{digits(value,0,4),digits(value,5,2),digits(value,8,2),digits(value,11,2),digits(value,14,2),digits(value,17,2)};
    validate(local);
    std::size_t position = 19;
    if (position < value.size() && value[position] == '.')
    {
        const std::size_t start = ++position;
        while (position < value.size() && std::isdigit(static_cast<unsigned char>(value[position]))) ++position;
        if (position == start) codec_fail();
    }
    int offset = 0;
    if (position < value.size() && value[position] == 'Z') ++position;
    else if (position + 6U <= value.size() && (value[position] == '+' || value[position] == '-'))
    {
        const int sign = value[position] == '+' ? 1 : -1;
        const int hours = digits(value, position + 1U, 2);
        if (value[position + 3U] != ':') codec_fail();
        const int minutes = digits(value, position + 4U, 2);
        if (hours > 23 || minutes > 59) codec_fail();
        offset = sign * (hours * 3600 + minutes * 60);
        position += 6U;
    }
    else codec_fail();
    if (position != value.size()) codec_fail();
    return from_epoch(epoch(local) - offset);
}

DateTime parse_asn1_time(const Node &node)
{
    DateTime result;
    if (node.tag == 0x17 && node.content.size() == 13U && node.content.back() == 'Z')
    {
        const int year = digits(node.content, 0, 2);
        result = {year >= 50 ? 1900 + year : 2000 + year, digits(node.content,2,2), digits(node.content,4,2),
                  digits(node.content,6,2), digits(node.content,8,2), digits(node.content,10,2)};
    }
    else if (node.tag == 0x18 && node.content.size() == 15U && node.content.back() == 'Z')
    {
        result = {digits(node.content,0,4), digits(node.content,4,2), digits(node.content,6,2),
                  digits(node.content,8,2), digits(node.content,10,2), digits(node.content,12,2)};
    }
    else codec_fail();
    validate(result);
    return result;
}

Bytes time_value(const DateTime &value, bool generalized = false)
{
    const std::string formatted = rfc3339(value);
    std::string compact = generalized || value.year >= 2050 ? formatted.substr(0,4) : formatted.substr(2,2);
    compact += formatted.substr(5,2) + formatted.substr(8,2) + formatted.substr(11,2) + formatted.substr(14,2) + formatted.substr(17,2) + "Z";
    return tlv(static_cast<std::uint8_t>(generalized || value.year >= 2050 ? 0x18 : 0x17), bytes(compact));
}

std::string text_value(const Node &node)
{
    if (node.tag == 0x0c || node.tag == 0x13 || node.tag == 0x14 || node.tag == 0x16)
    {
        if (node.content.find('\0') != std::string_view::npos) codec_fail();
        return std::string{node.content};
    }
    if (node.tag == 0x1e && node.content.size() % 2U == 0)
    {
        std::string result;
        for (std::size_t index = 0; index < node.content.size(); index += 2U)
        {
            if (node.content[index] != '\0' || static_cast<unsigned char>(node.content[index + 1U]) < 0x20U) codec_fail();
            result.push_back(node.content[index + 1U]);
        }
        return result;
    }
    codec_fail();
}

std::string name_key(std::string_view value)
{
    static const std::map<std::string_view, std::string_view> names{
        {"2.5.4.3","CN"},{"2.5.4.6","C"},{"2.5.4.7","L"},{"2.5.4.8","ST"},{"2.5.4.10","O"},
        {"2.5.4.11","OU"},{"1.2.840.113549.1.9.1","emailAddress"},{"0.9.2342.19200300.100.1.25","DC"}};
    const auto found = names.find(value);
    return found == names.end() ? std::string{value} : std::string{found->second};
}

std::string name_oid(std::string_view value)
{
    static const std::map<std::string_view, std::string_view> names{
        {"CN","2.5.4.3"},{"C","2.5.4.6"},{"L","2.5.4.7"},{"ST","2.5.4.8"},{"O","2.5.4.10"},
        {"OU","2.5.4.11"},{"emailAddress","1.2.840.113549.1.9.1"},{"DC","0.9.2342.19200300.100.1.25"}};
    const auto found = names.find(value);
    if (found == names.end()) codec_fail();
    return std::string{found->second};
}

std::string parse_name(const Node &node)
{
    if (node.tag != 0x30) codec_fail();
    Reader rdns{node.content, 1};
    std::string result;
    while (!rdns.empty())
    {
        Reader set = child(rdns, rdns.read(0x31));
        bool first = true;
        while (!set.empty())
        {
            Reader attribute = child(set, set.read(0x30));
            const std::string type = decode_oid(attribute.read(0x06));
            const std::string value = text_value(attribute.read());
            attribute.finish();
            result += first ? "/" : "+";
            result += name_key(type) + "=" + value;
            first = false;
        }
        set.finish();
    }
    rdns.finish();
    return result;
}

Bytes encode_name(std::string_view subject)
{
    if (!subject.empty() && subject.front() == '/') subject.remove_prefix(1);
    Bytes body;
    while (!subject.empty())
    {
        const std::size_t slash = subject.find('/');
        const std::string_view part = subject.substr(0, slash);
        const std::size_t equal = part.find('=');
        if (part.empty() || equal == 0 || equal == std::string_view::npos || equal + 1U >= part.size()) codec_fail();
        const std::string_view key = part.substr(0, equal);
        const std::string_view value = part.substr(equal + 1U);
        if (value.size() > 1024U || value.find('\0') != std::string_view::npos) codec_fail();
        const std::uint8_t tag = key == "C" ? 0x13 : key == "emailAddress" || key == "DC" ? 0x16 : 0x0c;
        append(body, set_of(sequence({oid(name_oid(key)), tlv(tag, bytes(value))})));
        if (slash == std::string_view::npos) break;
        subject.remove_prefix(slash + 1U);
    }
    return sequence(body);
}

struct Extension {
    std::string oid;
    bool critical{};
    Bytes value;
};

std::vector<Extension> parse_extensions(const Node &node)
{
    if (node.tag != 0x30) codec_fail();
    Reader reader{node.content, 1};
    std::vector<Extension> result;
    std::set<std::string> seen;
    while (!reader.empty())
    {
        Reader extension = child(reader, reader.read(0x30));
        Extension parsed;
        parsed.oid = decode_oid(extension.read(0x06));
        if (!seen.insert(parsed.oid).second) codec_fail();
        if (!extension.empty() && extension.peek() == 0x01)
        {
            const Node critical = extension.read(0x01);
            if (critical.content.size() != 1 || static_cast<unsigned char>(critical.content.front()) != 0xffU) codec_fail();
            parsed.critical = true;
        }
        const Node value = extension.read(0x04);
        parsed.value = bytes(value.content);
        extension.finish();
        result.push_back(std::move(parsed));
    }
    return result;
}

const Extension *find_extension(const std::vector<Extension> &extensions, std::string_view wanted)
{
    const auto found = std::find_if(extensions.begin(), extensions.end(), [wanted](const Extension &value) {
        return value.oid == wanted;
    });
    return found == extensions.end() ? nullptr : &*found;
}

Bytes encode_extension(std::string_view id, bool critical, const Bytes &value)
{
    Bytes content = oid(id);
    if (critical) append(content, boolean(true));
    append(content, octet_string(value));
    return sequence(content);
}

enum class KeyKind { rsa, ec };

struct PublicKey {
    KeyKind kind{KeyKind::rsa};
    Bytes spki;
    Bytes bit_string;
    Bytes modulus;
    Bytes exponent;
    Bytes x;
    Bytes y;
};

struct SignatureAlgorithm {
    KeyKind kind{KeyKind::rsa};
    ano_crypto_signature_algorithm_t sdk{ANO_CRYPTO_SIGNATURE_RSA_PKCS1_V15_SHA256};
    std::string digest;
    std::string oid;
};

Node root(std::string_view der, std::uint8_t tag = 0x30)
{
    require_size(der.size());
    Reader reader{der};
    Node result = reader.read(tag);
    reader.finish();
    return result;
}

Bytes bit_string_value(const Node &node)
{
    if (node.tag != 0x03 || node.content.empty()) codec_fail();
    const unsigned unused = static_cast<unsigned char>(node.content.front());
    if (unused > 7 || (node.content.size() == 1 && unused != 0)) codec_fail();
    if (unused != 0 && (static_cast<unsigned char>(node.content.back()) & ((1U << unused) - 1U)) != 0) codec_fail();
    return bytes(node.content.substr(1));
}

void require_null_or_absent(Reader &algorithm)
{
    if (!algorithm.empty())
    {
        const Node parameters = algorithm.read(0x05);
        if (!parameters.content.empty()) codec_fail();
    }
    algorithm.finish();
}

SignatureAlgorithm parse_signature_algorithm(const Node &node)
{
    if (node.tag != 0x30) codec_fail();
    Reader algorithm{node.content, 1};
    const std::string id = decode_oid(algorithm.read(0x06));
    if (id == kOidSha256WithRsa || id == kOidSha384WithRsa || id == kOidSha512WithRsa)
    {
        require_null_or_absent(algorithm);
        if (id == kOidSha256WithRsa) return {KeyKind::rsa, ANO_CRYPTO_SIGNATURE_RSA_PKCS1_V15_SHA256, "sha256", id};
        if (id == kOidSha384WithRsa) return {KeyKind::rsa, ANO_CRYPTO_SIGNATURE_RSA_PKCS1_V15_SHA384, "sha384", id};
        return {KeyKind::rsa, ANO_CRYPTO_SIGNATURE_RSA_PKCS1_V15_SHA512, "sha512", id};
    }
    if (id == kOidEcdsaSha256)
    {
        algorithm.finish();
        return {KeyKind::ec, ANO_CRYPTO_SIGNATURE_ECDSA_P256_SHA256, "sha256", id};
    }
    unsupported_algorithm();
}

SignatureAlgorithm requested_signature_algorithm(std::string_view requested, KeyKind kind)
{
    std::string normalized;
    normalized.reserve(requested.size());
    for (const unsigned char ch : requested)
        normalized.push_back(ch == '-' || ch == ' ' ? '_' : static_cast<char>(std::tolower(ch)));
    if (normalized.empty()) normalized = "sha256";
    if (kind == KeyKind::rsa)
    {
        if (normalized == "sha256" || normalized == "rsa_with_sha256")
            return {kind, ANO_CRYPTO_SIGNATURE_RSA_PKCS1_V15_SHA256, "sha256", std::string{kOidSha256WithRsa}};
        if (normalized == "sha384" || normalized == "rsa_with_sha384")
            return {kind, ANO_CRYPTO_SIGNATURE_RSA_PKCS1_V15_SHA384, "sha384", std::string{kOidSha384WithRsa}};
        if (normalized == "sha512" || normalized == "rsa_with_sha512")
            return {kind, ANO_CRYPTO_SIGNATURE_RSA_PKCS1_V15_SHA512, "sha512", std::string{kOidSha512WithRsa}};
    }
    else if (normalized == "sha256" || normalized == "ecdsa_with_sha256")
        return {kind, ANO_CRYPTO_SIGNATURE_ECDSA_P256_SHA256, "sha256", std::string{kOidEcdsaSha256}};
    unsupported_algorithm();
}

Bytes encode_algorithm(const SignatureAlgorithm &algorithm)
{
    return algorithm.kind == KeyKind::rsa ? sequence({oid(algorithm.oid), null_value()}) : sequence({oid(algorithm.oid)});
}

PublicKey parse_spki(const Node &node)
{
    if (node.tag != 0x30) codec_fail();
    Reader spki{node.content, 1};
    Reader algorithm = child(spki, spki.read(0x30));
    const std::string id = decode_oid(algorithm.read(0x06));
    PublicKey key;
    if (id == kOidRsaEncryption)
    {
        require_null_or_absent(algorithm);
        key.kind = KeyKind::rsa;
    }
    else if (id == kOidEcPublicKey)
    {
        if (decode_oid(algorithm.read(0x06)) != kOidP256) unsupported_algorithm();
        algorithm.finish();
        key.kind = KeyKind::ec;
    }
    else unsupported_algorithm();
    const Node encoded_key = spki.read(0x03);
    key.bit_string = bit_string_value(encoded_key);
    spki.finish();
    key.spki = bytes(node.encoded);
    if (key.kind == KeyKind::rsa)
    {
        Reader rsa = child(spki, root(view(key.bit_string)));
        key.modulus = positive_integer(rsa.read(0x02), false);
        key.exponent = positive_integer(rsa.read(0x02), false);
        rsa.finish();
        if (key.modulus.size() != ANO_CRYPTO_RSA2048_MODULUS_SIZE || (key.modulus.front() & 0x80U) == 0 ||
            key.exponent != Bytes{0x01,0x00,0x01}) unsupported_algorithm();
    }
    else
    {
        if (key.bit_string.size() != 65U || key.bit_string.front() != 0x04) codec_fail();
        key.x.assign(key.bit_string.begin() + 1, key.bit_string.begin() + 33);
        key.y.assign(key.bit_string.begin() + 33, key.bit_string.end());
    }
    return key;
}

std::string format_ip(const Bytes &value)
{
    if (value.size() == 4U)
        return std::to_string(value[0]) + "." + std::to_string(value[1]) + "." + std::to_string(value[2]) + "." + std::to_string(value[3]);
    if (value.size() == 16U)
    {
        std::ostringstream out;
        out << std::hex << std::setfill('0');
        for (std::size_t index = 0; index < 16U; index += 2U)
        {
            if (index != 0) out << ':';
            out << std::setw(4) << ((static_cast<unsigned>(value[index]) << 8U) | value[index + 1U]);
        }
        return out.str();
    }
    codec_fail();
}

Bytes parse_ip(std::string_view value)
{
    if (value.find(':') == std::string_view::npos)
    {
        Bytes result;
        while (!value.empty())
        {
            const std::size_t dot = value.find('.');
            const std::string_view part = value.substr(0, dot);
            unsigned octet{};
            const auto [end, error] = std::from_chars(part.data(), part.data() + part.size(), octet);
            if (part.empty() || error != std::errc{} || end != part.data() + part.size() || octet > 255U) codec_fail();
            result.push_back(static_cast<std::uint8_t>(octet));
            if (dot == std::string_view::npos) break;
            value.remove_prefix(dot + 1U);
        }
        if (result.size() != 4U) codec_fail();
        return result;
    }
    const std::size_t compression = value.find("::");
    if (compression != std::string_view::npos && value.find("::", compression + 2U) != std::string_view::npos) codec_fail();
    auto parse_groups = [](std::string_view side) {
        std::vector<Bytes> result;
        while (!side.empty())
        {
            const std::size_t colon = side.find(':');
            const std::string_view part = side.substr(0, colon);
            unsigned group{};
            const auto [end, error] = std::from_chars(part.data(), part.data() + part.size(), group, 16);
            if (part.empty() || part.size() > 4U || error != std::errc{} || end != part.data() + part.size()) codec_fail();
            result.push_back(Bytes{static_cast<std::uint8_t>(group >> 8U), static_cast<std::uint8_t>(group)});
            if (colon == std::string_view::npos) break;
            side.remove_prefix(colon + 1U);
        }
        return result;
    };
    std::vector<Bytes> left = parse_groups(value.substr(0, compression));
    std::vector<Bytes> right = compression == std::string_view::npos ? std::vector<Bytes>{} : parse_groups(value.substr(compression + 2U));
    if ((compression == std::string_view::npos && left.size() != 8U) ||
        (compression != std::string_view::npos && left.size() + right.size() >= 8U)) codec_fail();
    Bytes result;
    for (const Bytes &group : left) append(result, group);
    if (compression != std::string_view::npos) result.insert(result.end(), (8U - left.size() - right.size()) * 2U, 0);
    for (const Bytes &group : right) append(result, group);
    if (result.size() != 16U) codec_fail();
    return result;
}

void parse_san(const Extension &extension, std::vector<std::string> &dns, std::vector<std::string> &ips)
{
    Reader names{root(view(extension.value)).content, 1};
    while (!names.empty())
    {
        const Node name = names.read();
        if (name.tag == 0x82)
        {
            if (name.content.empty() || name.content.size() > 253U || name.content.find('\0') != std::string_view::npos) codec_fail();
            dns.emplace_back(name.content);
        }
        else if (name.tag == 0x87) ips.push_back(format_ip(bytes(name.content)));
    }
}

struct ParsedCsr {
    Bytes der;
    Bytes cri;
    Bytes subject;
    std::string subject_text;
    PublicKey public_key;
    SignatureAlgorithm signature_algorithm;
    Bytes signature;
    std::vector<Extension> extensions;
};

ParsedCsr parse_csr_der(const Bytes &der)
{
    const Node outer = root(view(der));
    Reader request{outer.content, 1};
    const Node cri_node = request.read(0x30);
    const Node signature_algorithm = request.read(0x30);
    const Node signature = request.read(0x03);
    request.finish();

    Reader cri{cri_node.content, 2};
    if (positive_integer(cri.read(0x02)) != Bytes{0}) codec_fail();
    const Node subject = cri.read(0x30);
    const Node spki = cri.read(0x30);
    const Node attributes = cri.read(0xa0);
    cri.finish();

    std::vector<Extension> extensions;
    Reader attrs{attributes.content, 3};
    bool found_extensions = false;
    while (!attrs.empty())
    {
        Reader attribute = child(attrs, attrs.read(0x30));
        const std::string id = decode_oid(attribute.read(0x06));
        const Node values = attribute.read(0x31);
        attribute.finish();
        if (id == kOidExtensionRequest)
        {
            if (found_extensions) codec_fail();
            Reader set = child(attribute, values);
            extensions = parse_extensions(set.read(0x30));
            set.finish();
            found_extensions = true;
        }
    }
    ParsedCsr result;
    result.der = der;
    result.cri = bytes(cri_node.encoded);
    result.subject = bytes(subject.encoded);
    result.subject_text = parse_name(subject);
    result.public_key = parse_spki(spki);
    result.signature_algorithm = parse_signature_algorithm(signature_algorithm);
    if (result.signature_algorithm.kind != result.public_key.kind) codec_fail();
    result.signature = bit_string_value(signature);
    result.extensions = std::move(extensions);
    return result;
}

struct ParsedCertificate {
    Bytes der;
    Bytes tbs;
    Bytes serial;
    Bytes issuer;
    std::string issuer_text;
    Bytes subject;
    std::string subject_text;
    DateTime not_before;
    DateTime not_after;
    PublicKey public_key;
    SignatureAlgorithm signature_algorithm;
    Bytes signature;
    std::vector<Extension> extensions;
};

ParsedCertificate parse_certificate_der(const Bytes &der)
{
    const Node outer = root(view(der));
    Reader certificate{outer.content, 1};
    const Node tbs_node = certificate.read(0x30);
    const Node outer_algorithm = certificate.read(0x30);
    const Node outer_signature = certificate.read(0x03);
    certificate.finish();
    ParsedCertificate result;
    result.der = der;
    result.tbs = bytes(tbs_node.encoded);
    result.signature_algorithm = parse_signature_algorithm(outer_algorithm);
    result.signature = bit_string_value(outer_signature);

    Reader tbs{tbs_node.content, 2};
    if (!tbs.empty() && tbs.peek() == 0xa0)
    {
        Reader version = child(tbs, tbs.read(0xa0));
        const Bytes value = positive_integer(version.read(0x02));
        version.finish();
        if (value.size() != 1 || value.front() > 2) codec_fail();
    }
    result.serial = positive_integer(tbs.read(0x02), false);
    const SignatureAlgorithm tbs_algorithm = parse_signature_algorithm(tbs.read(0x30));
    if (tbs_algorithm.oid != result.signature_algorithm.oid) codec_fail();
    const Node issuer = tbs.read(0x30);
    result.issuer = bytes(issuer.encoded);
    result.issuer_text = parse_name(issuer);
    Reader validity = child(tbs, tbs.read(0x30));
    result.not_before = parse_asn1_time(validity.read());
    result.not_after = parse_asn1_time(validity.read());
    validity.finish();
    const Node subject = tbs.read(0x30);
    result.subject = bytes(subject.encoded);
    result.subject_text = parse_name(subject);
    result.public_key = parse_spki(tbs.read(0x30));
    if (!tbs.empty() && (tbs.peek() == 0x81 || tbs.peek() == 0x82)) codec_fail();
    if (!tbs.empty())
    {
        Reader explicit_extensions = child(tbs, tbs.read(0xa3));
        result.extensions = parse_extensions(explicit_extensions.read(0x30));
        explicit_extensions.finish();
    }
    tbs.finish();
    return result;
}

ParsedCertificate parse_certificate_pem(std::string_view pem)
{
    return parse_certificate_der(decode_pem(pem, {"CERTIFICATE"}).der);
}

struct PrivateKey {
    PublicKey public_key;
    Bytes private_exponent;
    Bytes prime1;
    Bytes prime2;
    Bytes exponent1;
    Bytes exponent2;
    Bytes coefficient;
    Bytes scalar;
};

PrivateKey parse_rsa_private(const Bytes &der)
{
    Reader rsa{root(view(der)).content, 1};
    if (positive_integer(rsa.read(0x02)) != Bytes{0}) codec_fail();
    PrivateKey result;
    result.public_key.kind = KeyKind::rsa;
    result.public_key.modulus = positive_integer(rsa.read(0x02), false);
    if (result.public_key.modulus.size() != ANO_CRYPTO_RSA2048_MODULUS_SIZE ||
        (result.public_key.modulus.front() & 0x80U) == 0) unsupported_algorithm();
    result.public_key.exponent = positive_integer(rsa.read(0x02), false);
    result.private_exponent = padded(positive_integer(rsa.read(0x02), false), 256U);
    result.prime1 = padded(positive_integer(rsa.read(0x02), false), 128U);
    result.prime2 = padded(positive_integer(rsa.read(0x02), false), 128U);
    result.exponent1 = padded(positive_integer(rsa.read(0x02), false), 128U);
    result.exponent2 = padded(positive_integer(rsa.read(0x02), false), 128U);
    result.coefficient = padded(positive_integer(rsa.read(0x02), false), 128U);
    rsa.finish();
    if (result.public_key.exponent != Bytes{0x01,0x00,0x01}) unsupported_algorithm();
    return result;
}

PrivateKey parse_ec_private(const Bytes &der, bool p256_from_outer)
{
    Reader ec{root(view(der)).content, 1};
    if (positive_integer(ec.read(0x02)) != Bytes{1}) codec_fail();
    PrivateKey result;
    result.public_key.kind = KeyKind::ec;
    result.scalar = padded(bytes(ec.read(0x04).content), 32U);
    bool p256 = p256_from_outer;
    bool public_point = false;
    while (!ec.empty())
    {
        if (ec.peek() == 0xa0)
        {
            Reader parameters = child(ec, ec.read(0xa0));
            if (decode_oid(parameters.read(0x06)) != kOidP256) unsupported_algorithm();
            parameters.finish();
            p256 = true;
        }
        else if (ec.peek() == 0xa1)
        {
            Reader public_key = child(ec, ec.read(0xa1));
            const Bytes point = bit_string_value(public_key.read(0x03));
            public_key.finish();
            if (point.size() != 65U || point.front() != 0x04) codec_fail();
            result.public_key.bit_string = point;
            result.public_key.x.assign(point.begin() + 1, point.begin() + 33);
            result.public_key.y.assign(point.begin() + 33, point.end());
            public_point = true;
        }
        else codec_fail();
    }
    if (!p256 || !public_point) unsupported_algorithm();
    return result;
}

PrivateKey parse_pkcs8(const Bytes &der)
{
    Reader info{root(view(der)).content, 1};
    const Bytes version = positive_integer(info.read(0x02));
    if (version != Bytes{0}) codec_fail();
    Reader algorithm = child(info, info.read(0x30));
    const std::string id = decode_oid(algorithm.read(0x06));
    bool p256 = false;
    if (id == kOidRsaEncryption) require_null_or_absent(algorithm);
    else if (id == kOidEcPublicKey)
    {
        p256 = decode_oid(algorithm.read(0x06)) == kOidP256;
        algorithm.finish();
        if (!p256) unsupported_algorithm();
    }
    else unsupported_algorithm();
    const Bytes private_der = bytes(info.read(0x04).content);
    if (!info.empty()) codec_fail();
    return id == kOidRsaEncryption ? parse_rsa_private(private_der) : parse_ec_private(private_der, p256);
}

PrivateKey parse_private_key(std::string_view pem)
{
    const PemBlock block = decode_pem(pem, {"PRIVATE KEY", "RSA PRIVATE KEY", "EC PRIVATE KEY"}, kMaxKeyInput);
    if (block.label == "PRIVATE KEY") return parse_pkcs8(block.der);
    if (block.label == "RSA PRIVATE KEY") return parse_rsa_private(block.der);
    return parse_ec_private(block.der, false);
}

class KeyHandle final {
public:
    KeyHandle() = default;
    explicit KeyHandle(ano_crypto_csp_handle_t value) : value_{value} {}
    ~KeyHandle() { if (value_ != ANO_CRYPTO_CSP_INVALID_HANDLE) (void)ano_crypto_key_destroy(value_); }
    KeyHandle(const KeyHandle &) = delete;
    KeyHandle &operator=(const KeyHandle &) = delete;
    KeyHandle(KeyHandle &&other) noexcept : value_{std::exchange(other.value_, ANO_CRYPTO_CSP_INVALID_HANDLE)} {}
    KeyHandle &operator=(KeyHandle &&other) noexcept
    {
        if (this != &other)
        {
            if (value_ != ANO_CRYPTO_CSP_INVALID_HANDLE) (void)ano_crypto_key_destroy(value_);
            value_ = std::exchange(other.value_, ANO_CRYPTO_CSP_INVALID_HANDLE);
        }
        return *this;
    }
    [[nodiscard]] ano_crypto_csp_handle_t get() const noexcept { return value_; }
private:
    ano_crypto_csp_handle_t value_{ANO_CRYPTO_CSP_INVALID_HANDLE};
};

[[noreturn]] void provider_fail(std::string_view code) { fail(code); }

void check_import_status(ano_crypto_status_t status)
{
    if (status == ANO_CRYPTO_OK) return;
    if (status == ANO_CRYPTO_ERR_NOT_INITIALIZED || status == ANO_CRYPTO_ERR_FATAL_STATE || status == ANO_CRYPTO_ERR_SELF_TEST_FAILED)
        provider_fail("provider.not_ready");
    if (status == ANO_CRYPTO_ERR_UNSUPPORTED_ALGORITHM || status == ANO_CRYPTO_ERR_UNSUPPORTED_PARAMETER)
        provider_fail("provider.algorithm_mismatch");
    provider_fail("provider.key_parse_failed");
}

KeyHandle import_public_key(const PublicKey &key)
{
    ano_crypto_csp_handle_t handle = ANO_CRYPTO_CSP_INVALID_HANDLE;
    ano_crypto_status_t status;
    if (key.kind == KeyKind::rsa)
        status = ano_crypto_rsa_key_import(key.modulus.data(), key.modulus.size(), key.exponent.data(), key.exponent.size(),
            nullptr, 0, nullptr, 0, nullptr, 0, nullptr, 0, nullptr, 0, nullptr, 0,
            ANO_CRYPTO_KEY_FLAG_NONE, &handle);
    else
        status = ano_crypto_ec_p256_key_import(key.x.data(), key.x.size(), key.y.data(), key.y.size(), nullptr, 0,
            ANO_CRYPTO_KEY_FLAG_NONE, &handle);
    check_import_status(status);
    if (handle == ANO_CRYPTO_CSP_INVALID_HANDLE) provider_fail("provider.not_ready");
    return KeyHandle{handle};
}

KeyHandle import_private_key(const PrivateKey &key)
{
    ano_crypto_csp_handle_t handle = ANO_CRYPTO_CSP_INVALID_HANDLE;
    ano_crypto_status_t status;
    if (key.public_key.kind == KeyKind::rsa)
        status = ano_crypto_rsa_key_import(
            key.public_key.modulus.data(), key.public_key.modulus.size(), key.public_key.exponent.data(), key.public_key.exponent.size(),
            key.private_exponent.data(), key.private_exponent.size(), key.prime1.data(), key.prime1.size(),
            key.prime2.data(), key.prime2.size(), key.exponent1.data(), key.exponent1.size(),
            key.exponent2.data(), key.exponent2.size(), key.coefficient.data(), key.coefficient.size(),
            ANO_CRYPTO_KEY_FLAG_NONE, &handle);
    else
        status = ano_crypto_ec_p256_key_import(
            key.public_key.x.data(), key.public_key.x.size(), key.public_key.y.data(), key.public_key.y.size(),
            key.scalar.data(), key.scalar.size(), ANO_CRYPTO_KEY_FLAG_NONE, &handle);
    check_import_status(status);
    if (handle == ANO_CRYPTO_CSP_INVALID_HANDLE) provider_fail("provider.not_ready");
    return KeyHandle{handle};
}

bool same_public_key(const PublicKey &left, const PublicKey &right)
{
    if (left.kind != right.kind) return false;
    return left.kind == KeyKind::rsa ? left.modulus == right.modulus && left.exponent == right.exponent
                                     : left.x == right.x && left.y == right.y;
}

struct SigningEvidence {
    std::string operation;
    std::string key_algorithm;
    std::string requested_algorithm;
};

struct SigningKey {
    KeyHandle handle;
    SignatureAlgorithm algorithm;
    SigningEvidence evidence;
};

bool blank(std::string_view value)
{
    return value.empty() || std::all_of(value.begin(), value.end(), [](unsigned char ch) { return std::isspace(ch) != 0; });
}

bool windows_path(std::string_view value)
{
    return value.size() >= 3U && std::isalpha(static_cast<unsigned char>(value[0])) && value[1] == ':' &&
           (value[2] == '\\' || value[2] == '/');
}

std::filesystem::path file_reference(std::string_view key_ref)
{
    if (blank(key_ref) || key_ref.find('\0') != std::string_view::npos) provider_fail("provider.invalid_reference");
    if (!windows_path(key_ref))
    {
        const std::size_t colon = key_ref.find(':');
        if (colon != std::string_view::npos)
        {
            std::string scheme{key_ref.substr(0, colon)};
            std::transform(scheme.begin(), scheme.end(), scheme.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
            if (scheme != "file") provider_fail("provider.unavailable");
            key_ref.remove_prefix(colon + 1U);
        }
    }
    if (blank(key_ref) || key_ref.find('\0') != std::string_view::npos) provider_fail("provider.invalid_reference");
    return std::filesystem::path{std::string{key_ref}};
}

bool production_mode()
{
    const char *raw = std::getenv("ANOPKI_ENV");
    if (raw == nullptr) return false;
    std::string value{raw};
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    value.erase(value.begin(), std::find_if(value.begin(), value.end(), [](unsigned char ch) { return !std::isspace(ch); }));
    value.erase(std::find_if(value.rbegin(), value.rend(), [](unsigned char ch) { return !std::isspace(ch); }).base(), value.end());
    return value == "production";
}

std::string read_key_file(const std::filesystem::path &path)
{
    std::error_code error;
    if (!std::filesystem::exists(path, error)) provider_fail(error ? "provider.not_ready" : "provider.key_not_found");
    if (!std::filesystem::is_regular_file(path, error) || error) provider_fail("provider.not_ready");
    const std::uintmax_t size = std::filesystem::file_size(path, error);
    if (error || size == 0 || size > kMaxKeyInput) provider_fail("provider.key_parse_failed");
    std::ifstream input{path, std::ios::binary};
    if (!input) provider_fail("provider.not_ready");
    std::string result(static_cast<std::size_t>(size), '\0');
    input.read(result.data(), static_cast<std::streamsize>(result.size()));
    if (!input || input.peek() != std::char_traits<char>::eof()) provider_fail("provider.not_ready");
    return result;
}

SigningKey resolve_signing_key(
    std::string operation,
    const std::string &key_ref,
    std::string requested,
    const PublicKey &expected)
{
    if (blank(key_ref) || key_ref.find('\0') != std::string::npos) provider_fail("provider.invalid_reference");
    if (production_mode()) provider_fail("provider.exportability_violation");
    const std::filesystem::path path = file_reference(key_ref);
    PrivateKey parsed;
    try { parsed = parse_private_key(read_key_file(path)); }
    catch (const UnsupportedAlgorithm &) { provider_fail("provider.algorithm_mismatch"); }
    catch (const CodecError &) { provider_fail("provider.key_parse_failed"); }
    SignatureAlgorithm algorithm;
    try { algorithm = requested_signature_algorithm(requested, parsed.public_key.kind); }
    catch (const CodecError &) { provider_fail("provider.algorithm_mismatch"); }
    if (!same_public_key(parsed.public_key, expected)) provider_fail("provider.key_binding_mismatch");
    KeyHandle handle = import_private_key(parsed);
    SigningEvidence evidence{std::move(operation), parsed.public_key.kind == KeyKind::rsa ? "rsa" : "ecdsa", requested};
    return {std::move(handle), std::move(algorithm), std::move(evidence)};
}

Bytes ecdsa_raw_to_der(const Bytes &raw)
{
    if (raw.size() != 64U) codec_fail();
    Bytes r(raw.begin(), raw.begin() + 32);
    Bytes s(raw.begin() + 32, raw.end());
    if (std::all_of(r.begin(), r.end(), [](std::uint8_t v) { return v == 0; }) ||
        std::all_of(s.begin(), s.end(), [](std::uint8_t v) { return v == 0; })) codec_fail();
    return sequence({integer(r), integer(s)});
}

Bytes ecdsa_der_to_raw(const Bytes &der)
{
    Reader signature{root(view(der)).content, 1};
    Bytes r = padded(positive_integer(signature.read(0x02), false), 32U);
    Bytes s = padded(positive_integer(signature.read(0x02), false), 32U);
    signature.finish();
    append(r, s);
    return r;
}

Bytes sign(const SigningKey &key, const Bytes &message)
{
    const std::size_t expected = key.algorithm.kind == KeyKind::rsa ? ANO_CRYPTO_RSA2048_SIGNATURE_SIZE : ANO_CRYPTO_ECDSA_P256_SIGNATURE_SIZE;
    Bytes result(expected);
    std::size_t written = 0;
    const ano_crypto_status_t status = ano_crypto_signature_sign(
        key.handle.get(), key.algorithm.sdk, message.data(), message.size(), result.data(), result.size(), &written);
    if (status == ANO_CRYPTO_ERR_NOT_INITIALIZED || status == ANO_CRYPTO_ERR_FATAL_STATE || status == ANO_CRYPTO_ERR_SELF_TEST_FAILED)
        provider_fail("provider.not_ready");
    if (status != ANO_CRYPTO_OK || written != expected) provider_fail("provider.sign_failed");
    result.resize(written);
    return result;
}

bool verify(const PublicKey &key, const SignatureAlgorithm &algorithm, const Bytes &message, const Bytes &encoded_signature)
{
    if (key.kind != algorithm.kind) return false;
    Bytes signature;
    try { signature = key.kind == KeyKind::ec ? ecdsa_der_to_raw(encoded_signature) : encoded_signature; }
    catch (const CodecError &) { return false; }
    try
    {
        KeyHandle handle = import_public_key(key);
        return ano_crypto_signature_verify(handle.get(), algorithm.sdk, message.data(), message.size(), signature.data(), signature.size()) == ANO_CRYPTO_OK;
    }
    catch (const std::runtime_error &) { return false; }
}

Bytes digest(std::string_view algorithm, const Bytes &input)
{
    if (algorithm == "sha1")
    {
        Bytes result(ANO_CRYPTO_OCSP_CERTID_SHA1_DIGEST_SIZE);
        std::size_t written{};
        if (ano_crypto_ocsp_certid_sha1_digest(input.data(), input.size(), result.data(), result.size(), &written) != ANO_CRYPTO_OK || written != result.size())
            provider_fail("provider.not_ready");
        return result;
    }
    ano_crypto_hash_algorithm_t sdk;
    std::size_t size;
    if (algorithm == "sha256") { sdk = ANO_CRYPTO_HASH_ALG_SHA256; size = 32U; }
    else if (algorithm == "sha384") { sdk = ANO_CRYPTO_HASH_ALG_SHA384; size = 48U; }
    else if (algorithm == "sha512") { sdk = ANO_CRYPTO_HASH_ALG_SHA512; size = 64U; }
    else codec_fail();
    Bytes result(size);
    std::size_t written{};
    if (ano_crypto_hash_digest(sdk, input.data(), input.size(), result.data(), result.size(), &written) != ANO_CRYPTO_OK || written != result.size())
        provider_fail("provider.not_ready");
    return result;
}

Bytes random_serial()
{
    std::size_t context_size{};
    if (ano_crypto_random_context_size(&context_size) != ANO_CRYPTO_OK || context_size == 0 || context_size > kMaxKeyInput)
        provider_fail("provider.not_ready");
    Bytes context(context_size);
    if (ano_crypto_random_init(context.data(), context.size(), nullptr, 0, ANO_CRYPTO_RANDOM_FLAG_NONE) != ANO_CRYPTO_OK)
        provider_fail("provider.not_ready");
    Bytes serial(8U);
    const ano_crypto_status_t generated = ano_crypto_random_generate(
        context.data(), serial.data(), serial.size(), nullptr, 0, ANO_CRYPTO_RANDOM_FLAG_NONE);
    const ano_crypto_status_t uninitialized = ano_crypto_random_uninit(context.data(), context.size());
    if (generated != ANO_CRYPTO_OK || uninitialized != ANO_CRYPTO_OK) provider_fail("provider.not_ready");
    serial.front() |= 0x80U;
    return serial;
}

std::string json_escape(std::string_view value)
{
    std::string result;
    for (const unsigned char ch : value)
    {
        if (ch == '\\' || ch == '"') { result.push_back('\\'); result.push_back(static_cast<char>(ch)); }
        else if (ch < 0x20U) codec_fail();
        else result.push_back(static_cast<char>(ch));
    }
    return result;
}

void write_evidence(const SigningEvidence &evidence)
{
    const char *raw = std::getenv("ANOPKI_CORE_SIGNING_EVIDENCE_FILE");
    if (raw == nullptr || *raw == '\0') return;
    const std::filesystem::path path{raw};
    std::ofstream output{path, std::ios::binary | std::ios::trunc};
    if (!output) provider_fail("provider.evidence_failed");
    output << "{\"schema_version\":1,\"evidence_source\":\"core_signing\",\"operation\":\""
           << json_escape(evidence.operation)
           << "\",\"provider_id\":\"file\",\"provider_class\":\"file\",\"provider_readiness\":\"ready\""
              ",\"provider_exportability\":\"exportable\",\"reference_class\":\"file\",\"key_algorithm\":\""
           << json_escape(evidence.key_algorithm) << "\",\"requested_signature_algorithm\":\""
           << json_escape(evidence.requested_algorithm)
           << "\",\"issuer_binding_verified\":true,\"fallback_used\":false,\"result_code\":\"ok\"}\n";
    output.close();
    if (!output)
    {
        std::error_code ignored;
        std::filesystem::remove(path, ignored);
        provider_fail("provider.evidence_failed");
    }
}

bool key_usage_bit(const Extension *extension, unsigned bit)
{
    if (extension == nullptr) return false;
    const Node encoded = root(view(extension->value), 0x03);
    if (encoded.content.empty()) codec_fail();
    const unsigned unused = static_cast<unsigned char>(encoded.content.front());
    if (unused > 7 || encoded.content.size() < 2U) codec_fail();
    const std::size_t byte = 1U + bit / 8U;
    return byte < encoded.content.size() && (static_cast<unsigned char>(encoded.content[byte]) & (0x80U >> (bit % 8U))) != 0;
}

bool certificate_is_ca(const ParsedCertificate &certificate)
{
    const Extension *extension = find_extension(certificate.extensions, kOidBasicConstraints);
    if (extension == nullptr) return false;
    Reader constraints{root(view(extension->value)).content, 1};
    bool ca = false;
    if (!constraints.empty() && constraints.peek() == 0x01)
    {
        const Node value = constraints.read(0x01);
        if (value.content.size() != 1 || static_cast<unsigned char>(value.content.front()) != 0xffU) codec_fail();
        ca = true;
    }
    if (!constraints.empty()) (void)positive_integer(constraints.read(0x02));
    constraints.finish();
    return ca;
}

bool has_eku(const ParsedCertificate &certificate, std::string_view wanted)
{
    const Extension *extension = find_extension(certificate.extensions, kOidExtendedKeyUsage);
    if (extension == nullptr) return false;
    Reader usages{root(view(extension->value)).content, 1};
    bool found = false;
    while (!usages.empty()) found = decode_oid(usages.read(0x06)) == wanted || found;
    return found;
}

std::vector<std::string> dns_constraints(const Extension *extension, std::uint8_t wanted)
{
    std::vector<std::string> result;
    if (extension == nullptr) return result;
    Reader constraints{root(view(extension->value)).content, 1};
    while (!constraints.empty())
    {
        const Node group = constraints.read();
        if (group.tag != 0xa0 && group.tag != 0xa1) codec_fail();
        if (group.tag != wanted) continue;
        Reader subtrees{group.content, 2};
        while (!subtrees.empty())
        {
            Reader subtree = child(subtrees, subtrees.read(0x30));
            const Node base = subtree.read();
            if (base.tag == 0x82) result.emplace_back(base.content);
            while (!subtree.empty()) (void)subtree.read();
        }
    }
    return result;
}

bool dns_matches(std::string value, std::string constraint)
{
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    std::transform(constraint.begin(), constraint.end(), constraint.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
    if (constraint.empty() || value.empty()) return false;
    if (constraint.front() == '.') return value.size() >= constraint.size() && value.ends_with(constraint);
    return value == constraint || (value.size() > constraint.size() && value.ends_with("." + constraint));
}

void validate_name_constraints(const ParsedCertificate &issuer, const std::vector<std::string> &names)
{
    const Extension *extension = find_extension(issuer.extensions, kOidNameConstraints);
    const auto permitted = dns_constraints(extension, 0xa0);
    const auto excluded = dns_constraints(extension, 0xa1);
    for (const std::string &name : names)
    {
        if (std::any_of(excluded.begin(), excluded.end(), [&](const std::string &value) { return dns_matches(name, value); }))
            fail("issue.issuer_not_ca");
        if (!permitted.empty() && !std::any_of(permitted.begin(), permitted.end(), [&](const std::string &value) { return dns_matches(name, value); }))
            fail("issue.issuer_not_ca");
    }
}

Bytes bit_string(const Bytes &value, unsigned unused = 0)
{
    if (unused > 7 || (value.empty() && unused != 0)) codec_fail();
    Bytes content{static_cast<std::uint8_t>(unused)};
    append(content, value);
    return tlv(0x03, content);
}

void validate_dns(std::string_view value)
{
    if (value.empty() || value.size() > 253U || value.find('\0') != std::string_view::npos) codec_fail();
    std::size_t label = 0;
    for (const unsigned char ch : value)
    {
        if (ch == '.') { if (label == 0 || label > 63U) codec_fail(); label = 0; }
        else { if (!(std::isalnum(ch) || ch == '-' || ch == '*')) codec_fail(); ++label; }
    }
    if (label == 0 || label > 63U) codec_fail();
}

Bytes san_value(const std::vector<std::string> &dns_names, const std::vector<std::string> &ip_addresses)
{
    if (dns_names.size() + ip_addresses.size() > kMaxCollection) codec_fail();
    Bytes names;
    for (const std::string &dns_name : dns_names)
    {
        validate_dns(dns_name);
        append(names, tlv(0x82, bytes(dns_name)));
    }
    for (const std::string &ip : ip_addresses) append(names, tlv(0x87, parse_ip(ip)));
    return sequence(names);
}

Bytes basic_constraints_value(const core::IssueRequest &request)
{
    if (!request.basic_constraints_ca && request.basic_constraints_max_path_len >= 0) codec_fail();
    Bytes content;
    if (request.basic_constraints_ca) append(content, boolean(true));
    if (request.basic_constraints_max_path_len >= 0) append(content, integer(static_cast<std::uint64_t>(request.basic_constraints_max_path_len)));
    return sequence(content);
}

Bytes key_usage_value(const std::vector<std::string> &values)
{
    static const std::map<std::string_view, unsigned> mapping{
        {"digital_signature",0},{"non_repudiation",1},{"key_encipherment",2},{"data_encipherment",3},
        {"key_agreement",4},{"key_cert_sign",5},{"crl_sign",6},{"encipher_only",7},{"decipher_only",8}};
    if (values.empty() || values.size() > mapping.size()) codec_fail();
    std::set<unsigned> bits;
    for (const std::string &value : values)
    {
        const auto found = mapping.find(value);
        if (found == mapping.end() || !bits.insert(found->second).second) codec_fail();
    }
    if ((bits.contains(7) || bits.contains(8)) && !bits.contains(4)) codec_fail();
    const unsigned highest = *bits.rbegin();
    Bytes encoded(highest / 8U + 1U);
    for (const unsigned bit : bits) encoded[bit / 8U] |= static_cast<std::uint8_t>(0x80U >> (bit % 8U));
    return bit_string(encoded, 7U - highest % 8U);
}

Bytes extended_key_usage_value(const std::vector<std::string> &values)
{
    static const std::map<std::string_view, std::string_view> mapping{
        {"server_auth","1.3.6.1.5.5.7.3.1"},{"client_auth","1.3.6.1.5.5.7.3.2"},
        {"code_signing","1.3.6.1.5.5.7.3.3"},{"email_protection","1.3.6.1.5.5.7.3.4"},
        {"time_stamping","1.3.6.1.5.5.7.3.8"},{"ocsp_signing",kOidOcspSigning}};
    if (values.empty() || values.size() > mapping.size()) codec_fail();
    Bytes content;
    std::set<std::string> seen;
    for (const std::string &value : values)
    {
        const auto found = mapping.find(value);
        if (found == mapping.end() || !seen.insert(value).second) codec_fail();
        append(content, oid(found->second));
    }
    return sequence(content);
}

Bytes authority_info_access_value(std::string_view url)
{
    if (url.empty() || url.size() > 2048U || url.find('\0') != std::string_view::npos) codec_fail();
    return sequence({sequence({oid(kOidCaIssuers), tlv(0x86, bytes(url))})});
}

Bytes crl_distribution_points_value(const std::vector<std::string> &urls)
{
    if (urls.empty() || urls.size() > kMaxCollection) codec_fail();
    Bytes points;
    for (const std::string &url : urls)
    {
        if (url.empty() || url.size() > 2048U || url.find('\0') != std::string::npos) codec_fail();
        append(points, sequence({tlv(0xa0, tlv(0xa0, tlv(0x86, bytes(url))))}));
    }
    return sequence(points);
}

Bytes certificate_extensions(const core::IssueRequest &request, const ParsedCsr &csr, const ParsedCertificate &issuer)
{
    Bytes extensions;
    if (request.basic_constraints_critical || request.basic_constraints_ca || request.basic_constraints_max_path_len >= 0)
        append(extensions, encode_extension(kOidBasicConstraints, request.basic_constraints_critical, basic_constraints_value(request)));
    if (!request.key_usage.empty())
        append(extensions, encode_extension(kOidKeyUsage, request.key_usage_critical, key_usage_value(request.key_usage)));
    if (!request.extended_key_usage.empty())
        append(extensions, encode_extension(kOidExtendedKeyUsage, request.extended_key_usage_critical, extended_key_usage_value(request.extended_key_usage)));
    if (request.subject_key_identifier)
    {
        Bytes identifier = digest("sha256", csr.public_key.bit_string);
        identifier.resize(20U);
        append(extensions, encode_extension(kOidSubjectKeyIdentifier, false, octet_string(identifier)));
    }
    if (request.authority_key_identifier)
    {
        Bytes identifier;
        const Extension *ski = find_extension(issuer.extensions, kOidSubjectKeyIdentifier);
        if (ski != nullptr) identifier = bytes(root(view(ski->value), 0x04).content);
        else { identifier = digest("sha256", issuer.public_key.bit_string); identifier.resize(20U); }
        append(extensions, encode_extension(kOidAuthorityKeyIdentifier, false, sequence({tlv(0x80, identifier)})));
    }
    if (!request.aia_url.empty())
        append(extensions, encode_extension(kOidAuthorityInfoAccess, false, authority_info_access_value(request.aia_url)));
    if (!request.crl_distribution_points.empty())
        append(extensions, encode_extension(kOidCrlDistributionPoints, false, crl_distribution_points_value(request.crl_distribution_points)));
    if (!request.dns_names.empty() || !request.ip_addresses.empty())
        append(extensions, encode_extension(kOidSubjectAltName, false, san_value(request.dns_names, request.ip_addresses)));
    return sequence(extensions);
}

ParsedCsr parse_and_verify_csr(std::string_view pem)
{
    ParsedCsr csr = parse_csr_der(decode_pem(pem, {"CERTIFICATE REQUEST", "NEW CERTIFICATE REQUEST"}).der);
    if (!verify(csr.public_key, csr.signature_algorithm, csr.cri, csr.signature)) codec_fail();
    return csr;
}

core::CsrInfo csr_info(const ParsedCsr &csr)
{
    core::CsrInfo result;
    result.subject = csr.subject_text;
    result.public_key_algorithm = csr.public_key.kind == KeyKind::rsa ? "rsa" : "ecdsa";
    result.public_key_size_bits = csr.public_key.kind == KeyKind::rsa ? 2048 : 256;
    result.signature_algorithm = csr.signature_algorithm.digest;
    for (const Extension &extension : csr.extensions)
    {
        result.extension_oids.push_back(extension.oid);
        if (extension.oid == kOidSubjectAltName) parse_san(extension, result.dns_names, result.ip_addresses);
    }
    return result;
}

std::int64_t now_seconds()
{
    return std::chrono::duration_cast<std::chrono::seconds>(std::chrono::system_clock::now().time_since_epoch()).count();
}

void validate_issuer(const ParsedCertificate &issuer, const std::vector<std::string> &dns_names)
{
    if (!certificate_is_ca(issuer)) fail("issue.issuer_not_ca");
    const Extension *usage = find_extension(issuer.extensions, kOidKeyUsage);
    if (usage != nullptr && !key_usage_bit(usage, 5)) fail("issue.issuer_not_ca");
    const std::int64_t now = now_seconds();
    if (epoch(issuer.not_before) > now || epoch(issuer.not_after) < now) fail("issue.issuer_not_ca");
    validate_name_constraints(issuer, dns_names);
}

std::pair<DateTime, DateTime> issue_times(const core::IssueRequest &request)
{
    const std::int64_t now = now_seconds();
    DateTime before = request.not_before.empty() ? from_epoch(now) : parse_rfc3339(request.not_before);
    DateTime after = request.not_after.empty() ? from_epoch(now + 90LL * 24LL * 60LL * 60LL) : parse_rfc3339(request.not_after);
    if (epoch(before) >= epoch(after)) codec_fail();
    return {before, after};
}

}  // namespace

core::CsrInfo inspect_csr_pem(const std::string &csr_pem)
{
    try { return csr_info(parse_and_verify_csr(csr_pem)); }
    catch (const CodecError &) { fail("csr.parse_failed"); }
    catch (const std::runtime_error &error)
    {
        if (std::string_view{error.what()}.starts_with("provider.")) fail("csr.parse_failed");
        throw;
    }
}

core::IssueResult issue_certificate(const core::IssueRequest &request)
{
    ParsedCsr csr;
    try { csr = parse_and_verify_csr(request.csr_pem); }
    catch (const CodecError &) { fail("issue.csr_parse_failed"); }
    catch (const std::runtime_error &error)
    {
        if (std::string_view{error.what()}.starts_with("provider.")) fail("issue.csr_parse_failed");
        throw;
    }

    ParsedCertificate issuer;
    try { issuer = parse_certificate_pem(request.issuer_certificate_pem); }
    catch (const CodecError &) { fail("issue.issuer_certificate_parse_failed"); }
    try { validate_issuer(issuer, request.dns_names); }
    catch (const CodecError &) { fail("issue.issuer_not_ca"); }

    SigningKey signing_key = resolve_signing_key(
        "certificate_issue", request.issuer_key_ref, request.signature_algorithm, issuer.public_key);
    try
    {
        const auto [not_before, not_after] = issue_times(request);
        const Bytes serial = random_serial();
        const Bytes subject = request.subject.empty() ? csr.subject : encode_name(request.subject);
        if (parse_name(root(view(subject))).empty()) codec_fail();
        Bytes tbs_content = tlv(0xa0, integer(2));
        append(tbs_content, integer(serial));
        append(tbs_content, encode_algorithm(signing_key.algorithm));
        append(tbs_content, issuer.subject);
        append(tbs_content, sequence({time_value(not_before), time_value(not_after)}));
        append(tbs_content, subject);
        append(tbs_content, csr.public_key.spki);
        const Bytes extensions = certificate_extensions(request, csr, issuer);
        if (extensions != Bytes{0x30, 0x00}) append(tbs_content, tlv(0xa3, extensions));
        const Bytes tbs = sequence(tbs_content);
        Bytes signature = sign(signing_key, tbs);
        if (signing_key.algorithm.kind == KeyKind::ec) signature = ecdsa_raw_to_der(signature);
        const Bytes certificate = sequence({tbs, encode_algorithm(signing_key.algorithm), bit_string(signature)});

        core::IssueResult result;
        result.certificate_pem = encode_pem("CERTIFICATE", certificate);
        result.serial_number = decimal_string(serial);
        result.subject = parse_name(root(view(subject)));
        if (!result.subject.empty() && result.subject.front() == '/') result.subject.erase(0, 1);
        result.not_before = rfc3339(not_before);
        result.not_after = rfc3339(not_after);
        write_evidence(signing_key.evidence);
        return result;
    }
    catch (const CodecError &) { fail("issue.certificate_create_failed"); }
}

int reason_code(std::string_view reason)
{
    static const std::map<std::string_view, int> reasons{
        {"",0},{"unspecified",0},{"key_compromise",1},{"ca_compromise",2},{"affiliation_changed",3},
        {"superseded",4},{"cessation_of_operation",5},{"privilege_withdrawn",9}};
    const auto found = reasons.find(reason);
    if (found == reasons.end()) codec_fail();
    return found->second;
}

Bytes enumerated(unsigned value)
{
    if (value > 127U) codec_fail();
    return tlv(0x0a, Bytes{static_cast<std::uint8_t>(value)});
}

struct ParsedCrl {
    std::string issuer;
    int revoked_count{};
    std::string number;
};

ParsedCrl parse_crl(const Bytes &der)
{
    const Node outer = root(view(der));
    Reader crl{outer.content, 1};
    const Node tbs_node = crl.read(0x30);
    const SignatureAlgorithm outer_algorithm = parse_signature_algorithm(crl.read(0x30));
    const Bytes signature = bit_string_value(crl.read(0x03));
    crl.finish();
    if (outer_algorithm.kind == KeyKind::rsa)
    {
        if (signature.size() != 256U) codec_fail();
    }
    else (void)ecdsa_der_to_raw(signature);

    Reader tbs{tbs_node.content, 2};
    if (positive_integer(tbs.read(0x02)) != Bytes{1}) codec_fail();
    const SignatureAlgorithm tbs_algorithm = parse_signature_algorithm(tbs.read(0x30));
    if (tbs_algorithm.oid != outer_algorithm.oid) codec_fail();
    const Node issuer = tbs.read(0x30);
    ParsedCrl result;
    result.issuer = parse_name(issuer);
    (void)parse_asn1_time(tbs.read());
    (void)parse_asn1_time(tbs.read());
    if (!tbs.empty() && tbs.peek() == 0x30)
    {
        Reader revoked = child(tbs, tbs.read(0x30));
        while (!revoked.empty())
        {
            Reader entry = child(revoked, revoked.read(0x30));
            (void)positive_integer(entry.read(0x02), false);
            (void)parse_asn1_time(entry.read());
            if (!entry.empty()) (void)parse_extensions(entry.read(0x30));
            entry.finish();
            ++result.revoked_count;
        }
    }
    if (!tbs.empty())
    {
        Reader explicit_extensions = child(tbs, tbs.read(0xa0));
        const std::vector<Extension> extensions = parse_extensions(explicit_extensions.read(0x30));
        explicit_extensions.finish();
        const Extension *number = find_extension(extensions, kOidCrlNumber);
        if (number != nullptr) result.number = decimal_string(positive_integer(root(view(number->value), 0x02)));
    }
    tbs.finish();
    return result;
}

core::GenerateCRLResult generate_crl(const core::GenerateCRLRequest &request)
{
    ParsedCertificate issuer;
    try { issuer = parse_certificate_pem(request.issuer_certificate_pem); }
    catch (const CodecError &) { fail("crl.issuer_parse_failed"); }
    if (request.crl_number < 0) fail("crl.create_failed");
    SigningKey signing_key = resolve_signing_key("crl_generate_sign", request.issuer_key_ref, "sha256", issuer.public_key);
    try
    {
        const DateTime this_update = parse_rfc3339(request.this_update);
        const DateTime next_update = parse_rfc3339(request.next_update);
        if (epoch(this_update) >= epoch(next_update) || request.revoked_certificates.size() > kMaxCollection) codec_fail();
        struct Entry { Bytes serial; DateTime time; int reason; };
        std::vector<Entry> entries;
        for (const core::RevokedCertificate &value : request.revoked_certificates)
            entries.push_back({decimal_bytes(value.serial_number), parse_rfc3339(value.revoked_at), reason_code(value.reason)});
        std::sort(entries.begin(), entries.end(), [](const Entry &left, const Entry &right) {
            return left.serial.size() != right.serial.size() ? left.serial.size() < right.serial.size() : left.serial < right.serial;
        });
        Bytes revoked;
        for (const Entry &entry : entries)
        {
            const Bytes reason = encode_extension(kOidCrlReason, false, enumerated(static_cast<unsigned>(entry.reason)));
            append(revoked, sequence({integer(entry.serial), time_value(entry.time), sequence({reason})}));
        }
        const Bytes crl_number = encode_extension(
            kOidCrlNumber, false, integer(static_cast<std::uint64_t>(request.crl_number)));
        Bytes tbs_content = integer(1);
        append(tbs_content, encode_algorithm(signing_key.algorithm));
        append(tbs_content, issuer.subject);
        append(tbs_content, time_value(this_update));
        append(tbs_content, time_value(next_update));
        if (!entries.empty()) append(tbs_content, sequence(revoked));
        append(tbs_content, tlv(0xa0, sequence({crl_number})));
        const Bytes tbs = sequence(tbs_content);
        Bytes signature = sign(signing_key, tbs);
        if (signing_key.algorithm.kind == KeyKind::ec) signature = ecdsa_raw_to_der(signature);
        core::GenerateCRLResult result{
            encode_pem("X509 CRL", sequence({tbs, encode_algorithm(signing_key.algorithm), bit_string(signature)}))};
        write_evidence(signing_key.evidence);
        return result;
    }
    catch (const CodecError &) { fail("crl.create_failed"); }
}

core::CRLInfo inspect_crl_der(const std::string &crl_der)
{
    try
    {
        const ParsedCrl parsed = parse_crl(bytes(crl_der));
        return {parsed.issuer, parsed.revoked_count, parsed.number};
    }
    catch (const CodecError &) { fail("crl.parse_failed"); }
}

core::CRLInfo inspect_crl_pem(const std::string &crl_pem)
{
    try
    {
        const ParsedCrl parsed = parse_crl(decode_pem(crl_pem, {"X509 CRL"}).der);
        return {parsed.issuer, parsed.revoked_count, parsed.number};
    }
    catch (const CodecError &) { fail("crl.parse_failed"); }
}

std::string normalize_hash(std::string_view value)
{
    std::string result;
    for (const unsigned char ch : value)
        if (ch != '-' && ch != '_') result.push_back(static_cast<char>(std::tolower(ch)));
    if (result.empty()) result = "sha1";
    if (result != "sha1" && result != "sha256" && result != "sha384" && result != "sha512") codec_fail();
    return result;
}

std::string hash_oid(std::string_view value)
{
    if (value == "sha1") return std::string{kOidSha1};
    if (value == "sha256") return std::string{kOidSha256};
    if (value == "sha384") return std::string{kOidSha384};
    if (value == "sha512") return std::string{kOidSha512};
    codec_fail();
}

std::string hash_from_algorithm(const Node &node)
{
    Reader algorithm{node.content, 1};
    const std::string id = decode_oid(algorithm.read(0x06));
    require_null_or_absent(algorithm);
    if (id == kOidSha1) return "sha1";
    if (id == kOidSha256) return "sha256";
    if (id == kOidSha384) return "sha384";
    if (id == kOidSha512) return "sha512";
    codec_fail();
}

struct ParsedCertId {
    Bytes der;
    Bytes serial;
    Bytes issuer_name_hash;
    Bytes issuer_key_hash;
    std::string hash_algorithm;
};

ParsedCertId parse_cert_id(const Node &node)
{
    if (node.tag != 0x30) codec_fail();
    Reader id{node.content, 1};
    ParsedCertId result;
    result.der = bytes(node.encoded);
    result.hash_algorithm = hash_from_algorithm(id.read(0x30));
    result.issuer_name_hash = bytes(id.read(0x04).content);
    result.issuer_key_hash = bytes(id.read(0x04).content);
    result.serial = positive_integer(id.read(0x02), false);
    id.finish();
    const std::size_t expected = result.hash_algorithm == "sha1" ? 20U : result.hash_algorithm == "sha256" ? 32U :
                                 result.hash_algorithm == "sha384" ? 48U : 64U;
    if (result.issuer_name_hash.size() != expected || result.issuer_key_hash.size() != expected) codec_fail();
    return result;
}

struct ParsedOcspRequest {
    std::vector<ParsedCertId> ids;
    Bytes nonce;
    bool has_nonce{};
};

ParsedOcspRequest parse_ocsp_request(const Bytes &der)
{
    Reader request{root(view(der)).content, 1};
    Reader tbs = child(request, request.read(0x30));
    if (!request.empty()) codec_fail();
    request.finish();
    if (!tbs.empty() && tbs.peek() == 0xa0)
    {
        Reader version = child(tbs, tbs.read(0xa0));
        if (positive_integer(version.read(0x02)) != Bytes{0}) codec_fail();
        version.finish();
    }
    if (!tbs.empty() && tbs.peek() == 0xa1) codec_fail();
    Reader list = child(tbs, tbs.read(0x30));
    ParsedOcspRequest result;
    while (!list.empty())
    {
        Reader one = child(list, list.read(0x30));
        result.ids.push_back(parse_cert_id(one.read(0x30)));
        if (!one.empty())
        {
            Reader single_extensions = child(one, one.read(0xa0));
            (void)parse_extensions(single_extensions.read(0x30));
            single_extensions.finish();
        }
        one.finish();
    }
    if (result.ids.empty()) codec_fail();
    if (!tbs.empty())
    {
        Reader explicit_extensions = child(tbs, tbs.read(0xa2));
        const std::vector<Extension> extensions = parse_extensions(explicit_extensions.read(0x30));
        explicit_extensions.finish();
        const Extension *nonce = find_extension(extensions, kOidOcspNonce);
        if (nonce != nullptr)
        {
            result.nonce = bytes(root(view(nonce->value), 0x04).content);
            if (result.nonce.empty() || result.nonce.size() > 1024U) codec_fail();
            result.has_nonce = true;
        }
    }
    tbs.finish();
    return result;
}

core::OCSPRequestInfo inspect_ocsp_request_der(const std::string &request_der)
{
    try
    {
        const ParsedOcspRequest parsed = parse_ocsp_request(bytes(request_der));
        core::OCSPRequestInfo result;
        result.has_nonce = parsed.has_nonce;
        result.nonce_hex = hex(parsed.nonce);
        for (const ParsedCertId &id : parsed.ids)
            result.certificates.push_back({decimal_string(id.serial), hex(id.issuer_name_hash), hex(id.issuer_key_hash), id.hash_algorithm});
        return result;
    }
    catch (const CodecError &) { fail("ocsp.parse_failed"); }
}

core::OCSPIssuerInfo inspect_ocsp_issuer_pem(
    const std::string &issuer_certificate_pem,
    const std::string &hash_algorithm)
{
    ParsedCertificate issuer;
    try { issuer = parse_certificate_pem(issuer_certificate_pem); }
    catch (const CodecError &) { fail("ocsp.issuer_parse_failed"); }
    try
    {
        const std::string normalized = normalize_hash(hash_algorithm);
        return {hex(digest(normalized, issuer.subject)), hex(digest(normalized, issuer.public_key.bit_string)), normalized};
    }
    catch (const CodecError &) { fail("ocsp.create_failed"); }
}

std::string status_key(
    std::string_view serial,
    std::string_view algorithm,
    std::string_view name_hash,
    std::string_view key_hash)
{
    return std::string{serial} + '\0' + std::string{algorithm} + '\0' + std::string{name_hash} + '\0' + std::string{key_hash};
}

int ocsp_reason(std::string_view reason)
{
    return reason_code(reason);
}

void validate_ocsp_signer(const ParsedCertificate &certificate)
{
    const std::int64_t now = now_seconds();
    if (epoch(certificate.not_before) > now || epoch(certificate.not_after) <= now)
        fail("ocsp.responder_invalid");
    if (certificate_is_ca(certificate)) return;
    const Extension *usage = find_extension(certificate.extensions, kOidKeyUsage);
    if (usage != nullptr && !key_usage_bit(usage, 0)) fail("ocsp.responder_invalid");
    if (!has_eku(certificate, kOidOcspSigning)) fail("ocsp.responder_invalid");
}

Bytes response_cert_status(const core::OCSPCertificateStatus &status)
{
    if (status.status == "good") return tlv(0x80, {});
    if (status.status == "unknown") return tlv(0x82, {});
    if (status.status != "revoked") codec_fail();
    const DateTime revoked = parse_rfc3339(status.revoked_at);
    Bytes content = time_value(revoked, true);
    append(content, tlv(0xa0, enumerated(static_cast<unsigned>(ocsp_reason(status.revocation_reason)))));
    return tlv(0xa1, content);
}

core::GenerateOCSPResponseResult generate_ocsp_response(const core::GenerateOCSPResponseRequest &request)
{
    ParsedOcspRequest ocsp_request;
    try { ocsp_request = parse_ocsp_request(bytes(request.request_der)); }
    catch (const CodecError &) { fail("ocsp.parse_failed"); }
    ParsedCertificate signer;
    try { signer = parse_certificate_pem(request.issuer_certificate_pem); }
    catch (const UnsupportedAlgorithm &) { provider_fail("provider.algorithm_mismatch"); }
    catch (const CodecError &) { fail("ocsp.issuer_parse_failed"); }
    try { validate_ocsp_signer(signer); }
    catch (const CodecError &) { fail("ocsp.responder_invalid"); }
    SigningKey signing_key = resolve_signing_key("ocsp_response_sign", request.issuer_key_ref, "sha256", signer.public_key);
    try
    {
        const DateTime this_update = parse_rfc3339(request.this_update);
        const DateTime next_update = parse_rfc3339(request.next_update);
        if (epoch(this_update) >= epoch(next_update) || request.certificates.size() > kMaxCollection) codec_fail();
        std::map<std::string, core::OCSPCertificateStatus> statuses;
        for (const core::OCSPCertificateStatus &status : request.certificates)
        {
            (void)decimal_bytes(status.serial_number);
            std::string key = status.serial_number;
            if (!status.hash_algorithm.empty() || !status.issuer_name_hash.empty() || !status.issuer_key_hash.empty())
            {
                const std::string algorithm = normalize_hash(status.hash_algorithm);
                const Bytes name_hash = unhex(status.issuer_name_hash);
                const Bytes key_hash = unhex(status.issuer_key_hash);
                const std::size_t expected = algorithm == "sha1" ? 20U : algorithm == "sha256" ? 32U : algorithm == "sha384" ? 48U : 64U;
                if (name_hash.size() != expected || key_hash.size() != expected) codec_fail();
                key = status_key(status.serial_number, algorithm, hex(name_hash), hex(key_hash));
            }
            const auto [_, inserted] = statuses.emplace(key, status);
            if (!inserted) codec_fail();
        }
        Bytes responses;
        for (const ParsedCertId &id : ocsp_request.ids)
        {
            const std::string serial = decimal_string(id.serial);
            auto found = statuses.find(status_key(serial, id.hash_algorithm, hex(id.issuer_name_hash), hex(id.issuer_key_hash)));
            if (found == statuses.end()) found = statuses.find(serial);
            core::OCSPCertificateStatus status;
            if (found == statuses.end()) { status.serial_number = serial; status.status = "unknown"; }
            else status = found->second;
            Bytes single = id.der;
            append(single, response_cert_status(status));
            append(single, time_value(this_update, true));
            append(single, tlv(0xa0, time_value(next_update, true)));
            append(responses, sequence(single));
        }
        Bytes response_data = tlv(0xa1, signer.subject);
        append(response_data, time_value(from_epoch(now_seconds()), true));
        append(response_data, sequence(responses));
        if (ocsp_request.has_nonce)
        {
            const Bytes nonce = encode_extension(kOidOcspNonce, false, octet_string(ocsp_request.nonce));
            append(response_data, tlv(0xa1, sequence({nonce})));
        }
        const Bytes tbs = sequence(response_data);
        Bytes signature = sign(signing_key, tbs);
        if (signing_key.algorithm.kind == KeyKind::ec) signature = ecdsa_raw_to_der(signature);
        const Bytes basic = sequence({
            tbs,
            encode_algorithm(signing_key.algorithm),
            bit_string(signature),
            tlv(0xa0, sequence({signer.der})),
        });
        const Bytes response_bytes = sequence({oid(kOidOcspBasic), octet_string(basic)});
        const Bytes response = sequence({enumerated(0), tlv(0xa0, response_bytes)});
        core::GenerateOCSPResponseResult result{std::string{view(response)}};
        write_evidence(signing_key.evidence);
        return result;
    }
    catch (const CodecError &) { fail("ocsp.create_failed"); }
}

core::ValidateOCSPResponderResult validate_ocsp_responder(
    const std::string &issuer_certificate_pem,
    const std::string &responder_certificate_pem)
{
    try
    {
        const ParsedCertificate issuer = parse_certificate_pem(issuer_certificate_pem);
        const ParsedCertificate responder = parse_certificate_pem(responder_certificate_pem);
        if (responder.issuer != issuer.subject || certificate_is_ca(responder)) codec_fail();
        const Extension *usage = find_extension(responder.extensions, kOidKeyUsage);
        if (usage != nullptr && !key_usage_bit(usage, 0)) codec_fail();
        if (!has_eku(responder, kOidOcspSigning)) codec_fail();
        const std::int64_t now = now_seconds();
        if (epoch(responder.not_before) > now || epoch(responder.not_after) <= now) codec_fail();
        if (!verify(issuer.public_key, responder.signature_algorithm, responder.tbs, responder.signature)) codec_fail();
        return {true};
    }
    catch (const CodecError &) { fail("ocsp.responder_invalid"); }
    catch (const std::runtime_error &error)
    {
        if (std::string_view{error.what()}.starts_with("provider.")) fail("ocsp.responder_invalid");
        throw;
    }
}

}  // namespace anopki::crypto::enterprise::pki
