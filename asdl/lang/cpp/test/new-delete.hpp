int * default_constructor_scalar() {
  return new int();
}

int ** default_constructor_pointer() {
  return new int*();
}

int * default_constructor_array() {
  return new int [12];
}

int * constructor_scalar() {
  return new int(1);
}

int ** constructor_pointer() {
  return new int*(nullptr);
}

int * constructor_array() {
  return new int [3]{1,2,3};
}

void delete_pointer(int * p) {
  delete p;
}

void delete_array(int * p) {
  delete [] p;
}
