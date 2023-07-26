void for_() {
  for(;;) {}

  for(0;;) {}
  for(;1;) {}
  for(;;2) {}

  for(0;1;2) 3;
  for(0;1;2) {3;4;}
}

void for_break() {
  for(;;) break;
}

void for_continue() {
  for(;;) continue;
}
