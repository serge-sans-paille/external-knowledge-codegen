__attribute__((aligned(16))) int a;
__attribute__((aligned)) int a_p;

int b;
extern __attribute__((alias("b"))) int c;
