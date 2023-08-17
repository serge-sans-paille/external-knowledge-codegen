struct foo {
  void bar();
  void bar(int i);
  void bar(int i) const;
  void babar(int i) &&;
  void babar(int i) &;
  void babar(int i) const &;
  virtual void bar(int i, int j);
  virtual void bar(int i, int j, int k) = 0;
  virtual void bar(float) final;
};

struct foofoo : foo {
  virtual void bar(int i, int j, int k) override;
};
