#ifndef OBJECT_H
#define OBJECT_H

#include <iostream>
#include <string>

namespace N {
class Object
{
public:
  Object(int i = 3) : m_i(i) {}
  // namespace is mandatory in the example because it is present in the AST
  Object(const N::Object& o);

  virtual ~Object();

//   int run(bool b);
  int run(bool b)
  {
    std::string s = "azer";
    if (b)
      return 0;
    else
    {
      float f1 = 0.11;
//       std::cerr << s << " " << b << std::endl;
      return 1;
    }
  }
private:
  int m_i = 23;
};
}

using namespace N;
int n = 2;

int f(int p=3)
{
  char c = 'c';
  c = c+2;
//   c += 1;
  return (p+1)*2;
}

#endif