struct empty {
};

struct some {
  int field;
};

struct nested {
  struct nest {
    int a;
  };
  int b;
};

struct list {
  int val;
  struct list * next;
};

// This is correctly modeled, but using a generated name
// struct { int x; } anonymous;


// This is correctly modeled, but split in two, as clang does
// struct foo { int x; } inline_decl;

struct nested_with_indirect_field {
  int val;
  struct {
    int indirect;
  };
};
