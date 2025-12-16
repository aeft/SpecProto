#!/usr/bin/env bash
set -e

VERSION=3.23.4
PARTIAL_VERSION=23.4
PREFIX="$(pwd)/third_party/protobuf"
ABSEIL_PREFIX="$(pwd)/third_party/abseil-cpp"

if [ -x "$PREFIX/bin/protoc" ]; then
  echo "[protobuf] already installed at $PREFIX"
  "$PREFIX/bin/protoc" --version
  exit 0
fi

echo "[protobuf] installing v$VERSION to $PREFIX"

mkdir -p third_party
cd third_party

# download and build abseil-cpp (dependency of protobuf)
if [ ! -d "abseil-cpp" ]; then
  git clone https://github.com/abseil/abseil-cpp.git
  cd abseil-cpp
  git checkout 20230125.3
  cd ..
fi

# build & install abseil-cpp
if [ ! -f "$ABSEIL_PREFIX/lib/cmake/absl/abslConfig.cmake" ]; then
  echo "[abseil-cpp] building and installing to $ABSEIL_PREFIX"
  cd abseil-cpp
  cmake -S . -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$ABSEIL_PREFIX" \
    -DCMAKE_CXX_STANDARD=17 \
    -DABSL_PROPAGATE_CXX_STD=ON \
    -DABSL_ENABLE_INSTALL=ON
  cmake --build build --parallel 4
  cmake --install build
  cd ..
  echo "[abseil-cpp] done"
else
  echo "[abseil-cpp] already installed at $ABSEIL_PREFIX"
fi

# download source
if [ ! -d "protobuf" ]; then
  curl -fL -o protobuf-${PARTIAL_VERSION}.tar.gz \
  https://github.com/protocolbuffers/protobuf/releases/download/v${PARTIAL_VERSION}/protobuf-${PARTIAL_VERSION}.tar.gz
  tar -xzf protobuf-${PARTIAL_VERSION}.tar.gz
  mv protobuf-${PARTIAL_VERSION} protobuf
fi

cd "protobuf"

# build & install (CMake)
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -Dprotobuf_BUILD_TESTS=OFF \
  -Dprotobuf_ABSL_PROVIDER=package \
  -DCMAKE_PREFIX_PATH="$ABSEIL_PREFIX"

cmake --build build --parallel 2
cmake --install build

echo "[protobuf] done"
echo "  protoc: $PREFIX/bin/protoc"
echo "  version: $("$PREFIX/bin/protoc" --version)"