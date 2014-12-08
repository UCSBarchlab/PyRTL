/* To compile this, you will need Sourcery CodeBench for MIPS on GNU/Linux or another MIPS cross-compiler.
 * http://www.mentor.com/embedded-software/sourcery-tools/sourcery-codebench/editions/lite-edition/
 * 
 * The command to compile your cross-compiled MIPS binary with CodeBench is:
 * mips-linux-gnu-gcc -march=r2k -nostartfiles -mlong-calls -msoft-float -static -fPIE mips-example.c
 *
 * This will create an a.out file compatible with our MIPS implementation.
 * Note that full instruction support is not present so dependence on libc will cause issues.
 */

#include <unistd.h>
#include <stdio.h>

/* Some syscalls are defined here. Feel free to add more.
 * In the MIPS pipeline syscall layer, syscalls start at 4000.
 * So syscall 1 is 4001 actually in the Python.
 * This is due to the C compiler targeting Linux O32 syscalls which range from 4000-4999.
 * It ends up essentially compiling to adding 4000 to whatever number syscall you choose.
 */
#define SYS_print_int 1
#define SYS_exit 10

void __start()
{
  syscall(SYS_print_int, strlen("hello world\n"));

  int i = 0;
  for (; i <= 10; ++i) syscall(SYS_print_int, i);

  syscall(SYS_exit, 42);
}
