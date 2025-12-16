// https://github.com/cmuparlay/parlaylib/blob/51017699dcc421f80479cdb238d3092233ad0d26/include/parlay/internal/get_time.h
#pragma once

#include <chrono>
#include <iomanip>
#include <iostream>
#include <string>

namespace parlay {
struct timer {
   private:
    using clock = std::chrono::high_resolution_clock;
    using time_t = clock::time_point;
    using duration_t = std::chrono::nanoseconds;
    duration_t total_so_far;
    time_t last;
    bool on;
    std::string name;

    void report(double time, std::string str) {
        std::ios::fmtflags cout_settings = std::cout.flags();
        std::cout.precision(4);
        std::cout << std::fixed;
        std::cout << name << ": ";
        if (str.length() > 0) std::cout << str << ": ";
        std::cout << time << " s" << std::endl;
        std::cout.flags(cout_settings);
    }

   public:
    timer(std::string name = "High-Resolution Timer", bool start_ = true)
        : total_so_far(duration_t::zero()), on(false), name(name) {
        if (start_) start();
    }

    auto get_time() { return clock::now(); }

    double diff(time_t t1, time_t t2) {
        return std::chrono::duration_cast<duration_t>(t1 - t2).count() / 1e9;
    }

    void start() {
        on = true;
        last = get_time();
    }

    double stop() {
        on = false;
        duration_t d = diff_as_duration(get_time(), last);
        total_so_far += d;
        return d.count() / 1e9;
    }

    void reset() {
        total_so_far = duration_t::zero();
        on = false;
    }

    double next_time() {
        if (!on) return 0.0;
        time_t t = get_time();
        duration_t td = diff_as_duration(t, last);
        total_so_far += td;
        last = t;
        return td.count() / 1e9;
    }

    double total_time() {
        if (on)
            return (total_so_far + diff_as_duration(get_time(), last)).count() / 1e9;
        else
            return total_so_far.count() / 1e9;
    }

    void next(std::string str) {
        if (on) report(next_time(), str);
    }

    void total() { report(total_time(), "total"); }

   private:
    duration_t diff_as_duration(time_t t1, time_t t2) {
        return std::chrono::duration_cast<duration_t>(t1 - t2);
    }
};
}  // namespace parlay