void foo() {
  int x;
  bool y = x; // implicit cast
  float z0 = (float)x;
  float z1 = x;
  float z2 = (int)x; // chained cast
  void * p0 = &x; // implicit pointer cast
  void * p1 = (void*)&x; // implicit pointer cast
  const void * p2 = &x;
  const void * p3 = (const void*)&x;
}

void bar() {
  int(1);
  static_cast<float>(1);
  unsigned long i;
  reinterpret_cast<long *>(&i);
}

