void empty();
void empty() {
}

// NOTE: parsed as above by clang.
// void empty_void(void);
// void empty_void(void) {
// }


void foo(int x);
void foo(int x) {
}

void bar(const int x, float *y) {
}

void variadic(int x, ...) {
}
