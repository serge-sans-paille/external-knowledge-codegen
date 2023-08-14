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
