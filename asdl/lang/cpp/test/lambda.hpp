void no_capture() {
  auto x = [](){};
  auto y = [](int a, float b){};
  auto z = [](int a){ return a;};
}

void with_capture(int X, int &Y) {
  auto x = [X](){ return X;};
  auto x_ref = [&X](){ return X;};
  auto y = [Y](){ return Y;};
  auto y_ref = [&Y](){ return Y;};
  auto z = [X,&Y](){ return X, Y;};
  auto z_p = [&X,Y](){ return X, Y;};
}
