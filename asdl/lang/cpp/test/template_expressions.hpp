/* scalar expressions */
template<int J>
int se0() {
  return J;
}
template<int J>
int se1() {
  return J + 1;
}
template<int J, int K>
int se2() {
  return J + K;
}

/* array decl */
template<int J>
void ad0() {
  int array[J];
}
