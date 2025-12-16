setup:
	mkdir -p ./dataset
	mkdir -p ./artifact
	mkdir -p ./artifact/build
	mkdir -p ./artifact/build/disable_type_prioritization
	mkdir -p ./artifact/generated
	mkdir -p ./artifact/result
	mkdir -p ./artifact/figure
	mkdir -p ./artifact/log

PREFIX ?= pprof_profile

PYTHON = .venv/bin/python3

PROTOC = third_party/protobuf/bin/protoc

gen_pb_py:
	$(PROTOC) --proto_path=./schema/ --python_out=./artifact/generated $(PREFIX).proto

gen_pb:
	$(PROTOC) --proto_path=./schema/ --cpp_out=./artifact/generated $(PREFIX).proto

gen_pbs:
	$(MAKE) gen_pb PREFIX=pprof_profile
	$(MAKE) gen_pb PREFIX=google_map
	$(MAKE) gen_pb PREFIX=walmart_product
	$(MAKE) gen_pb PREFIX=twitter_stream
	$(MAKE) gen_pb PREFIX=synth_wiki
	$(MAKE) gen_pb PREFIX=synth_tree

gen_desc:
	$(PROTOC) --include_imports --descriptor_set_out=./artifact/generated/${PREFIX}.desc ./schema/$(PREFIX).proto

GEN_OPTIONS ?= 

gen_parallel_pb: gen_pb gen_desc
	$(PYTHON) -m pbdecoder_gen.gen_from_proto ./schema/$(PREFIX).proto $(GEN_OPTIONS)

gen_parallel_pbs:
	$(MAKE) gen_parallel_pb PREFIX=pprof_profile GEN_OPTIONS="$(GEN_OPTIONS)"
	$(MAKE) gen_parallel_pb PREFIX=google_map GEN_OPTIONS="$(GEN_OPTIONS)"
	$(MAKE) gen_parallel_pb PREFIX=walmart_product GEN_OPTIONS="$(GEN_OPTIONS)"
	$(MAKE) gen_parallel_pb PREFIX=twitter_stream GEN_OPTIONS="$(GEN_OPTIONS)"
	$(MAKE) gen_parallel_pb PREFIX=synth_wiki GEN_OPTIONS="$(GEN_OPTIONS)"
	$(MAKE) gen_parallel_pb PREFIX=synth_tree GEN_OPTIONS="$(GEN_OPTIONS)"

PROTOBUF_DIR = third_party/protobuf
ABSEIL_DIR = third_party/abseil-cpp
BUILD ?= build
BUILD_DIR = ./artifact/$(BUILD)/$(PREFIX)

build_all:
	$(MAKE) build PREFIX=pprof_profile
	$(MAKE) build PREFIX=google_map
	$(MAKE) build PREFIX=walmart_product
	$(MAKE) build PREFIX=twitter_stream
	$(MAKE) build PREFIX=synth_wiki
	$(MAKE) build PREFIX=synth_tree

DEFINE ?= 

build: clean
	@echo "[BUILD] schema=$(PREFIX) build_dir=$(BUILD_DIR)"
	@mkdir -p $(BUILD_DIR)
	g++ -std=c++17 \
	artifact/generated/$(PREFIX).bl.cpp \
	artifact/generated/$(PREFIX).tpp.cpp \
	artifact/generated/$(PREFIX).spp.cpp \
	artifact/generated/$(PREFIX).pb.cc \
	artifact/generated/$(PREFIX).test.cpp \
	-I$(PROTOBUF_DIR)/include \
	-I$(ABSEIL_DIR)/include \
	-L$(PROTOBUF_DIR)/lib64 \
	-Wl,--start-group \
		-lprotobuf \
		-lutf8_range \
		-lutf8_validity \
		$(ABSEIL_DIR)/lib64/libabsl_*.a \
	-Wl,--end-group \
	-lpthread -fopenmp -O3 \
	$(DEFINE) \
	-o $(BUILD_DIR)/$(PREFIX).test

clean:
	@echo "[CLEAN] schema=$(PREFIX) build_dir=$(BUILD_DIR)"
	@rm -rf "$(BUILD_DIR)"

RUNS ?= 5
THREADS ?= 1

run:
	$(PYTHON) -m experiment.run --test_mode $(TEST_MODE) --dataset $(DATASET) --impl $(IMPL) --threads $(THREADS)

overall_execution_time:
	$(PYTHON) -m experiment.run --experiment overall_execution_time

overall_execution_time_fig:
	$(PYTHON) -m experiment.plot.overall_execution_time

memory_overhead:
	$(PYTHON) -m experiment.run --experiment memory_overhead

time_breakdown_spec:
	$(PYTHON) -m experiment.run --experiment time_breakdown_spec

time_breakdown_spec_fig:
	$(PYTHON) -m experiment.plot.time_breakdown_spec

benefits_of_type_prioritization:
	$(PYTHON) -m experiment.run --experiment benefits_of_type_prioritization

benefits_of_type_prioritization_fig:
	$(PYTHON) -m experiment.plot.benefits_of_type_prioritization

scalability_over_threads:
	$(PYTHON) -m experiment.run --experiment scalability_over_threads

scalability_over_threads_fig:
	$(PYTHON) -m experiment.plot.scalability_over_threads

scalability_over_size:
	$(PYTHON) -m experiment.run --experiment scalability_over_size

scalability_over_size_fig:
	$(PYTHON) -m experiment.plot.scalability_over_size

cost_breakdown_spec:
	$(PYTHON) -m experiment.run --experiment cost_breakdown_spec

memory_overhead_over_threads:
	$(PYTHON) -m experiment.run --experiment memory_overhead_over_threads