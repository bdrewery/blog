Title: btxld: No such file or directory
Tags: FreeBSD,tech

For years I have ran into this error while running `make installworld`:

	# make installworld
	[...]
	===> sys/boot/i386/boot2 (install)
	cc -Os  -fno-guess-branch-probability  -fomit-frame-pointer  -fno-unit-at-a-time  -mno-align-long-strings  -mrtd  -mregparm=3  -DUSE_XREAD  -DUFS1_AND_UFS2  -DFLAGS=0x80  -DSIOPRT=0x3f8  -DSIOFMT=0x3  -DSIOSPD=9600  -I/usr/src/sys/boot/i386/boot2/../../common  -I/usr/src/sys/boot/i386/boot2/../btx/lib -I.  -Wall -Waggregate-return -Wbad-function-cast -Wcast-align  -Wmissing-declarations -Wmissing-prototypes -Wnested-externs  -Wpointer-arith -Wshadow -Wstrict-prototypes -Wwrite-strings  -Winline --param max-inline-insns-single=100   -march=i386 -ffreestanding -mpreferred-stack-boundary=2  -mno-mmx -mno-3dnow -mno-sse -mno-sse2 -mno-sse3 -msoft-float -m32 -std=gnu99    -S -o boot2.s.tmp /usr/src/sys/boot/i386/boot2/boot2.c
	sed -e '/align/d' -e '/nop/d' < boot2.s.tmp > boot2.s
	rm -f boot2.s.tmp
	cc  -m32 -c boot2.s
	ld -static -N --gc-sections -nostdlib -m elf_i386_fbsd -Ttext 0x2000 -o boot2.out /usr/obj/usr/src/sys/boot/i386/boot2/../btx/lib/crt0.o boot2.o sio.o
	objcopy -S -O binary boot2.out boot2.bin
	btxld -v -E 0x2000 -f bin -b /usr/obj/usr/src/sys/boot/i386/boot2/../btx/btx/btx -l boot2.ldr  -o boot2.ld -P 1 boot2.bin
	btxld: No such file or directory
	*** [boot2.ld] Error code 1

	Stop in /usr/src/sys/boot/i386/boot2.
	*** [realinstall] Error code 1

This has [come](http://lists.freebsd.org/pipermail/freebsd-current/2010-June/018292.html), [up](http://lists.freebsd.org/pipermail/freebsd-amd64/2006-September/008849.html), [before](http://lists.freebsd.org/pipermail/freebsd-amd64/2004-August/001906.html).

Most of the posts mention bad timestamps or incorrect date. I've always been running ntpd though and running `make buildworld` before `make installworld`.

My longterm workaround was to `make -C /usr/src/sys/boot/i386` before running `make installworld`.

Recently this workaround stopped working for me. Looking into it more, I realized that I was applying custom patches to the src tree and then removing them before `make installworld`. This was changing timestamps of source files, causing a rebuild during `make installworld`. Changing my scripts to leave the patch applied until after everything is installed solves it.
