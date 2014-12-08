#include <unistd.h>
#include <stdio.h>

#define SYS_print_int 1
#define SYS_exit 10

void __start()
{
  syscall(SYS_print_int, strlen("hello world\n"));

  int i = 0;
  for (; i <= 10; ++i) syscall(SYS_print_int, i);

  syscall(44, 5, 6);

  syscall(SYS_exit, 42);
}
