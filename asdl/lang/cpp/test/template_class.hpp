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
