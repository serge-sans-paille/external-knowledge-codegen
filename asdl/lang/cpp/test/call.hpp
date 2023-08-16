void call_builtin() {
  __builtin_trap();
}

void foo(int, float);
void call_args(int i, float f) {
  return foo(i, f);
}

struct s {
  void foo() const;
};

void call_method(const s & obj) {
  (&obj)->foo();
  return obj.foo();
}
