void foo() {
  1, 2;
  1 ? 2 : 3;
  sizeof(int);
  sizeof(1);
  sizeof(1 + 3);
  alignof(int);
  alignof(1);
  alignof(1 + 3);
  (1 + 2) * 3;
}

int expr_stmt() {
  return ({int X = 4; X;});
}

void conditional_with_opitted_operands(int x, int y) {
  x ? : y;
}

void predefined() {
  __PRETTY_FUNCTION__;
  __func__;
    __FUNCTION__;
}
