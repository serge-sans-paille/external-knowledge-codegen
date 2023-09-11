// Template type
template<typename T>
struct forward_decl;

template<typename T, typename S>
struct multiple_params;

template<typename T>
struct decl {
  T member;
  const T * const_ptr_member;
};

template<typename T=int>
struct with_default;

// Template value
template<int T>
struct forward_decl_value;

template<int T, int S>
struct multiple_params_value;

template<int N>
struct decl_value {
  static const int member = N;
};

template<int T=3>
struct with_default_value;


// instantiation
using d = decl<int>;
using dv = decl_value<3>;

// declare variables
decl<float> dd_float;
decl<decl<float>> dd_type;
decl_value<8> dd8;

// specialization
template<>
struct decl<int> {
  int imember;
};

template<>
struct decl_value<5> {
  static const int member = 0;
};

// partial specialization
template<typename T0, typename T1>
struct foo;

template<typename T>
struct foo<T, float> {};

template<typename P>
struct foo<decl<P>, bool> {
  P p;
};

template<typename T, typename P>
struct foo<decl<P>, T> {
  P p;
};

template<typename T, typename P>
struct foo<T, decl<P>> {
  template<typename S>
  P doit(S);
};
