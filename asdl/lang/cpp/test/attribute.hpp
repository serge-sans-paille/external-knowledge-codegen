__attribute__((aligned(16))) int a;
__attribute__((aligned)) int a_p;

int b;
extern __attribute__((alias("b"))) int c;

void d(void*);
void e() {
  __attribute__((cleanup(d))) int f;
}

__attribute__((deprecated)) int g;
__attribute__((deprecated("too old"))) int g_p;

__attribute__((unavailable)) int h;
__attribute__((unavailable("too old"))) int h_p;
