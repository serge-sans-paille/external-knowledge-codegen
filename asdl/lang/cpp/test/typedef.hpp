typedef int simple;
typedef int * simple_ptr;
typedef const float qualified_simple;
typedef const int * simple_ptr_to_qualified;
typedef const int * const simple_qualified_ptr_to_qualified;

typedef int array[2];
typedef int matrix[2][3];
typedef int three_d[2][3][4];

typedef int* array_of_pointer[5];
typedef int (*pointer_to_array)[6];

typedef int (*function_pointer)(float);
typedef int (function_proto)(float, bool);
typedef int (*(array_of_functions[8]))(float, bool);
