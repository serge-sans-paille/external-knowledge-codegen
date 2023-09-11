auto x = 1;
const auto cx = 1;
const auto & cxr = 1;
decltype(auto) y = 2;
__auto_type z = 3;

auto foo() {
  return 1;
}

auto lambda = [](auto y) { return y; };

auto bar(int x) {
  return [&x](auto * z) { return *z + x; };
}
