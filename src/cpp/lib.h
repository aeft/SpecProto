#ifndef __LIB_H__
#define __LIB_H__
#include <fcntl.h>
#include <getopt.h>
#include <immintrin.h>
#include <nmmintrin.h>
#include <omp.h>
#include <sys/mman.h>
#include <sys/stat.h>

#include <cassert>
#include <cstring>
#include <deque>
#include <initializer_list>
#include <iostream>
#include <map>
#include <string>
#include <vector>

#include "get_time.h"

#define THROW_RUNTIME_ERROR(msg) \
    throw std::runtime_error(std::string(msg) + " at " + __FILE__ + ":" + std::to_string(__LINE__))

#define ASSERT_WITH_MSG(cond, msg)                                                 \
    do {                                                                           \
        if (!(cond)) {                                                             \
            std::cerr << "Assertion failed: " << (msg) << "\n"                     \
                      << "  File: " << __FILE__ << ", Line: " << __LINE__ << "\n"; \
            assert(cond);                                                          \
        }                                                                          \
    } while (0)

const size_t padding = 10;

struct Buffer {
    uint8_t* buffer;
    size_t size;

    Buffer(std::string& filename) {
        int fd = open(filename.c_str(), O_RDONLY);

        if (fd == -1) {
            THROW_RUNTIME_ERROR("file open failed");
        }

        struct stat sb;
        if (fstat(fd, &sb) == -1) {
            THROW_RUNTIME_ERROR("fstate failed");
        }
        this->size = sb.st_size;

        this->buffer =
            static_cast<uint8_t*>(mmap(NULL, this->size + padding, PROT_READ, MAP_PRIVATE, fd, 0u));
        if (this->buffer == MAP_FAILED) {
            THROW_RUNTIME_ERROR("mmap failed");
        }
    }
    ~Buffer() { assert(munmap(this->buffer, this->size + padding) == 0); }
};

#ifdef COUNT_TAG_BYTES
extern uint32_t stat_tag_bytes;
#endif

struct ByteStream {
    uint8_t* buffer;
    uint32_t curr;  // TODO should easily support int64
    uint32_t end;

    ByteStream(uint8_t* buffer, uint32_t curr, uint32_t end)
        : buffer(buffer), curr(curr), end(end) {}

    inline bool Done() { return curr >= end; }
    inline bool Skip(uint32_t len) {
        curr += len;
        return true;
    }

    inline bool readVarint32Strict(uint32_t& val) {
        val = 0;
        for (int i = 0; i < 5; i++) {
            uint32_t b = buffer[curr++];
            val |= (b & 0x7f) << (7 * i);
            if (b < 0x80) {
                return curr <= end;
            }
        }
        return false;
    }

    // external callers call ReadVarint
    inline bool readVarint32(uint32_t& val) {
        val = 0;
        // We relaxed the checks here. Sometimes we find that certain real-world datasets
        // doesn't fully match the schema; for example, an int32 was defined,
        // but the actual data is int64.
        for (int i = 0; i < 10; i++) {
            uint32_t b = buffer[curr++];
            val |= (b & 0x7f) << (7 * i);
            if (b < 0x80) {
                return curr <= end;
            }
        }
        return false;
    }

    // external callers call ReadVarint
    inline bool readVarint64(uint64_t& val) {
        val = 0;
        for (int i = 0; i < 10; i++) {
            uint64_t b = buffer[curr++];
            val |= (b & 0x7f) << (7 * i);
            if (b < 0x80) {
                return curr <= end;
            }
        }
        return false;
    }

    // recommand use ReadVarint instead of ReadVarint32 and ReadVarint64
    template <typename T>
    inline bool ReadVarint(T& val) {
        if (sizeof(T) <= 4) {
            uint32_t val_tmp;
            if (!readVarint32(val_tmp)) return false;
            val = val_tmp;
        } else {
            uint64_t val_tmp;
            if (!readVarint64(val_tmp)) return false;
            val = val_tmp;
        }
        return true;
    }

    inline bool ReadVarintLen(uint32_t& len) {
        uint32_t curr_tmp = curr;
        uint32_t shift = 0;
        for (len = 1; len <= 10; len++) {
            uint32_t b = buffer[curr_tmp++];
            if (b < 0x80) {
                return curr <= end;
            }
            shift += 7;
        }
        return false;
    }

    inline bool ReadTag(uint32_t& tag) {
#ifdef COUNT_TAG_BYTES
        uint32_t curr_tmp = curr;
        bool res = readVarint32Strict(tag);
        stat_tag_bytes += curr - curr_tmp;
        return res;
#else
        return readVarint32Strict(tag);
#endif
    }

    inline bool IsLenValid(uint32_t len) { return len <= end and curr + len <= end; }

    inline bool ReadLen(uint32_t& len) { return readVarint32Strict(len) and IsLenValid(len); }

    template <typename T>
    inline bool ReadFixed(T& val) {
        int size = sizeof(T);

        if (curr + size > end) {
            return false;
        }

        memcpy(&val, buffer + curr, size);

        curr += size;
        return true;
    }

    inline bool ReadString(std::string& val, uint32_t len) {
        if (curr + len > end or curr + len < curr) {
            return false;
        }
        val.assign((char*)buffer + curr, len);
        curr += len;
        return true;
    }

    inline bool ReadString(std::string& val) { return ReadString(val, end - curr); }

    inline bool ReadStringAppend(std::string& val, uint32_t len) {
        if (curr + len > end or curr + len < curr) {
            return false;
        }
        val.append(buffer + curr, buffer + curr + len);
        curr += len;
        return true;
    }

    inline bool ReadStringAppend(std::string& val) { return ReadStringAppend(val, end - curr); }

    // Note: we don't overwrite current value
    template <typename T>
    inline bool ReadPackedVarint(std::vector<T>& nums, uint32_t len) {
        uint32_t end_tmp = curr + len;
        if (end_tmp > end or end_tmp < curr) {
            return false;
        }

        T val;
        while (curr < end_tmp) {
            ReadVarint(val);
            nums.push_back(val);
        }

        return true;
    }

    template <typename T>
    inline bool ReadPackedVarint(std::vector<T>& nums) {
        return ReadPackedVarint(nums, end - curr);
    }

    // Note: we don't overwrite current value
    template <typename T>
    inline bool ReadPackedFixed(std::vector<T>& nums, uint32_t len) {
        uint32_t end_tmp = curr + len;
        if (end_tmp > end or end_tmp < curr) {
            return false;
        }

        T val;
        while (curr < end_tmp) {
            ReadFixed(val);
            nums.push_back(val);
        }

        return true;
    }

    template <typename T>
    inline bool ReadPackedFixed(std::vector<T>& nums) {
        return ReadPackedFixed(nums, end - curr);
    }
};

template <typename T>
inline void move_copy(std::vector<T>& dst, std::vector<T>&& src) {
    if (dst.size() == 0) {
        dst = std::move(src);
    } else {
        dst.insert(dst.end(), src.begin(), src.end());
    }
}

template <typename T>
inline void move_copy(std::vector<T>& dst, T src) {
    dst.push_back(std::move(src));
}

struct Args {
    std::string file_path;
    std::string test_mode;
    std::string impl;
    int runs;

    Args()
        : test_mode("C"),
          impl("BL"),
          runs(5) {}

    void print() {
        std::cout << file_path << "|" << test_mode << "|" << impl << "|" << runs << "\n";
    }
};

inline Args ReadArgs(int argc, char* argv[]) {
    Args result;

    static struct option long_options[] = {
        {"file_path", required_argument, 0, 0},
        {"test_mode", required_argument, 0, 0},
        {"impl", required_argument, 0, 0},
        {"runs", required_argument, 0, 0},
        {0, 0, 0, 0}  // End of options
    };

    int option_index = 0;
    int c;

    while ((c = getopt_long(argc, argv, "", long_options, &option_index)) != -1) {
        if (c == 0) {
            // Process options based on option_index
            std::string opt_name = long_options[option_index].name;

            if (opt_name == "file_path") {
                result.file_path = optarg;
            } else if (opt_name == "test_mode") {
                result.test_mode = optarg[0];
            } else if (opt_name == "impl") {
                result.impl = optarg;
            } else if (opt_name == "runs") {
                result.runs = std::stoi(optarg);
            }
        } else {
            break;
        }
    }

    return result;
}

#endif