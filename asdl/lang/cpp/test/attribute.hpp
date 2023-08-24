/*
 * variable attributes
 */

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

__attribute__ ((section ("INITDATA"))) int i;

__attribute__ ((unused)) int j;
__attribute__ ((used)) int k;

void l() {
  __attribute__((uninitialized)) int m;
}

__attribute__ ((vector_size (16))) int n;

__attribute__((visibility("hidden"))) int o;
__attribute__((weak)) int p;
__attribute__((retain)) int q;

__attribute__((tls_model ("local-exec"))) __thread int r;


struct s
{
  char t;
   __attribute__ ((packed)) int u[2];
};


/*
 * function attributes
 */
void f0 () { /* Do something. */; }
void f1 () __attribute__ ((weak)) __attribute__((alias ("f0")));

void f2 () __attribute__ ((aligned));
void f3 () __attribute__ ((aligned(8)));

struct s0 {
  s0 () __attribute__ ((aligned));
  ~s0 () __attribute__ ((aligned));
  operator int () const __attribute__ ((aligned));
  void m() noexcept __attribute__ ((aligned));
};

void* f4 (int, int) __attribute__ ((alloc_align (1)));

void* f5 (int, int) __attribute__ ((alloc_size (1)));
void* f6 (int, int) __attribute__ ((alloc_size (1, 2)));

void* f7 (int, int) __attribute__ ((always_inline));

void* f8 (int, int) __attribute__ ((cold));

void* f9 (int, int) __attribute__ ((constructor));
void* f10 (int, int) __attribute__ ((constructor(45)));
void* f11 (int, int) __attribute__ ((destructor));
void* f12 (int, int) __attribute__ ((destructor(54)));

void* f13 (int, int) __attribute__ ((deprecated));
void* f14 (int, int) __attribute__ ((deprecated("msg")));

void* f15 (int, int) __attribute__ ((unavailable));
void* f16 (int, int) __attribute__ ((unavailable("msg")));

void* f17 (int, int) __attribute__ ((error("msg")));

void* f18 (int, int) __attribute__ ((flatten));

int f19(void *, const char *, ...) __attribute__ ((format (printf, 2, 3)));

extern char * f20(char *my_domain, const char *my_format) __attribute__ ((format_arg (2)));

extern inline void* f21 (int, int) __attribute__ ((gnu_inline));

void* f22 (int, int) __attribute__ ((hot));

void * (*f23 ())();
void* f24 () __attribute__ ((ifunc("f23")));

void f25 (void*) __attribute__ ((interrupt));

void f26 (void*) __attribute__ ((leaf));

void* f27 (void*) __attribute__ ((malloc));

void* f28 (void*) __attribute__ ((no_instrument_function));

void* f29 (void*) __attribute__ ((no_profile_instrument_function));

void* f30 (void*) __attribute__ ((no_sanitize ("alignment", "object-size")));

void* f31 (void*) __attribute__ ((no_split_stack));

void* f32 (void*) __attribute__ ((noinline));

void* f33 (void*) __attribute__ ((nonnull));
void* f34 (void*) __attribute__ ((nonnull(1)));

void* f35 (void*) __attribute__ ((noreturn));
