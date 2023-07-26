void basic_jump() {

from:
  1;
  goto from;

}

void jump_loop() {
  while(1)
    goto target;
target:
  2;
}
