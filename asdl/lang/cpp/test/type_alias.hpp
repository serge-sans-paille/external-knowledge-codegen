using type = int;

using ::type;

// template version
template<class T>
using t_alias = T;

template<class T0, class T1>
using t_alias1 = T1;

template<class P>
struct alias_holder {
  template<class Q>
  using type0 = P;
  template<class Q>
  using type1 = Q;
};

// template template version

template <template <typename...> class O>
struct D {
  using type = void;
};

template <typename T> using P = typename T::P;

using p = D<P>;
p some();
