Title: Managing Role Based FreeBSD servers using meta packages and Poudriere
Tags: FreeBSD,ports,pkg,poudriere,tech

To simplify server management I create "meta" packages in FreeBSD ports that can generate a package with only dependencies on other packages. This allows to me to just install this 1 package on the target server and have it pull in all of the packages that I want on there. I assign each server specific "roles" and only install 1 or 2 packages per server depending on which roles they fulfill. The roles may be one of "dev", "web", "ports-dev", "jail", etc. This ensures that all servers fulfilling specific roles will always have the proper packages installed. For some applications, I use a dedicated jail with a meta package that only pulls in the required dependencies for that application to run. For instance, on a PHP application jail, the meta package may pull in nginx, php, eaccelerator, git, etc.

## Packages are created from ports

To create meta packages, define a port that requires the actual ports that should be installed. Then build packages for those meta ports.

### dev-meta port

#### /usr/ports/local/dev-meta/Makefile

This meta port will install *git*, *cscope* and *vim*. Which dependencies those pull in do not matter here.

	PORTNAME=	local-dev-meta
	PORTVERSION=	20130719
	CATEGORIES=     local
	MASTER_SITES=	# none
	DISTFILES=	# none
	EXTRACT_ONLY=	# none

	MAINTAINER=	local@localdomain.com
	COMMENT=	Meta port for dev packages

	NO_BUILD=	yes
	NO_WRKSUBDIR=	yes

	RUN_DEPENDS+=	git>0:${PORTSDIR}/devel/git
	RUN_DEPENDS+=	cscope>0:${PORTSDIR}/devel/cscope
	RUN_DEPENDS+=	vim-lite>0:${PORTSDIR}/editors/vim-lite

	do-install: build
		@${DO_NADA}

	.include <bsd.port.mk>

Note the _RUN\_DEPENDS_ line is depending on *package names*, not *binary names*. Any version will satisfy the dependency.

#### /usr/ports/local/dev-meta/pkg-descr

	Development meta port

#### /etc/make.conf

The _local_ category must be defined.

	VALID_CATEGORIES+=	local

### Building packages with Poudriere

[Poudriere](https://fossil.etoilebsd.net/poudriere) is a tool to build and test packages for FreeBSD. There is a detailed guide on [creating pkgng repositories](https://fossil.etoilebsd.net/poudriere/doc/trunk/doc/pkgng_repos.wiki) on the poudriere site, so I will only cover it briefly here.

Install poudriere on your build machine:

	build# make -C /usr/ports/ports-mgmt/poudriere install clean

Configure poudriere:

	build# cat >> /usr/local/etc/poudriere.conf
	BASEFS=/poudriere
	ZPOOL=tank
	# Directory where the CCACHE_DIR is in the host
	CCACHE_DIR=/usr/ccache
	# Directory to store distfiles on the host
	DISTFILES_CACHE=/mnt/distfiles
	^D
	build# mkdir /usr/local/etc/poudriere.d
	build# cat >> /usr/local/etc/poudriere.d/make.conf
	WITH_PKGNG=	yes
	^D

Create a jail and import your existing _/usr/ports_ tree as *system*:

	# Create jail
	build# poudriere jail -c -j 83amd64 -v 8.3-RELEASE -a amd64
	...
	# Add system's /usr/ports into poudriere
	build# poudriere ports -c -F -f none -M /usr/ports -p system
	...

Pick options for your meta package and dependencies:

	build# poudriere options -p system local/dev-meta

Now build the packages from the meta port using the *system* ports tree:

	build# poudriere bulk -j 83amd64 -p system local/dev-meta
	====>> Creating the reference jail... done
	====>> Mounting system devices for 83amd64-system
	====>> Mounting ports/packages/distfiles
	====>> Mounting ccache from: /usr/ccache
	====>> Mounting packages from: /poudriere/data/packages/83amd64-system
	====>> Mounting /var/db/ports from: /usr/local/etc/poudriere.d/options
	====>> Logs: /poudriere/data/logs/bulk/83amd64-system/2013-07-21_14h14m27s
	====>> Appending to make.conf: /usr/local/etc/poudriere.d/make.conf
	/etc/resolv.conf -> /poudriere/data/build/83amd64-system/ref/etc/resolv.conf
	====>> Starting jail 83amd64-system
	====>> Calculating ports order and dependencies
	====>> pkg package missing, skipping sanity
	====>> Cleaning the build queue
	====>> Building 53 packages using 14 builders
	====>> Starting/Cloning builders
	====>> [01] Starting build of ports-mgmt/pkg
	[...]
	====>> Creating pkgng repository
	Generating repository catalog in /packages: done!
	====>> Cleaning up
	====>> Umounting file systems
	====>> Built ports: ports-mgmt/pkg devel/ccache textproc/xmlcatmgr archivers/unzip lang/perl5.14 net/p5-Socket textproc/iso8879 textproc/xmlcharent converters/libiconv devel/gettext devel/m4 devel/libtool net/p5-IO-Socket-IP security/libgpg-error security/p5-Net-SSLeay textproc/docbook-410 textproc/docbook-420 textproc/docbook-430 textproc/docbook-440 textproc/docbook-450 textproc/docbook-500 textproc/docbook-sk textproc/docbook-xml textproc/docbook-xml-430 textproc/docbook-xml-440 devel/bison devel/boehm-gc devel/gmake textproc/docbook-xml-450 devel/pkgconf security/ca_root_nss security/p5-IO-Socket-SSL misc/getopt print/libpaper security/libgcrypt shells/bash textproc/docbook textproc/docbook-xsl textproc/libxml2 textproc/libxslt www/w3m ftp/curl lang/p5-Error lang/python27 mail/p5-Net-SMTP-SSL textproc/asciidoc textproc/expat2 textproc/xmlto devel/cscope devel/cvsps devel/git editors/vim-lite local/dev-meta

	====>> [83amd64-system] 53 packages built, 0 failures, 0 ignored, 0 skipped
	====>> Logs: /poudriere/data/logs/bulk/83amd64-system/2013-07-21_14h14m27s

The */poudriere/data/packages/83amd64-system* directory now contains the pkgng repository that needs to be served. This can be done over NFS, Samba, HTTP, FTP, etc. It is best to serve the */poudriere/data/packages* directory and create symlinks of the ABI name to the target. The ABI is a pkgng feature defined as _OS:REL:ARCH:BITS_. For instance, this build would be _freebsd:8:x86:64_.

	build# ln -s 83amd64-system /poudriere/data/packages/freebsd:8:x86:64

The repository is now ready for use on the target servers.

## Role based servers with packages

On the target server, the appropriate meta packages just need to be installed now.


First bootstrap the system with pkg if needed.

	dev# mkdir -p /usr/local/etc
	dev# echo 'PACKAGESITE=http://packages.domain.com/${ABI}' > /usr/local/etc/pkg.conf
	dev# pkg -v
	The package management tool is not yet installed on your system.
	Do you want to fetch and install it now? [y/N]: y
	Bootstrapping pkg please wait
	Installing pkg-1.1.4... done
	If you are upgrading from the old package format, first run:

	  # pkg2ng
	1.1.4

Now the `local/dev-meta` package can be installed:

	dev# pkg install local/dev-meta
	digests.txz                                                        100%   57KB  57.1KB/s  57.1KB/s   00:00
	packagesite.txz                                                    100%  323KB 323.3KB/s 323.3KB/s   00:00
	Incremental update completed, 0 packages processed:
	0 packages updated, 0 removed and 53 added.
	The following 42 packages will be installed:

		Installing libiconv: 1.14_1
		Installing xproto: 7.0.24
		Installing renderproto: 0.11.1
		Installing libXdmcp: 1.1.1
		Installing libXau: 1.0.8
		Installing pkgconf: 0.9.2_1
		Installing libpthread-stubs: 0.3_3
		Installing kbproto: 1.0.6
		Installing expat: 2.0.1_2
		Installing freetype2: 2.4.12_1
		Installing tcl: 8.5.14_1
		Installing openssl: 1.0.1_8
		Installing db42: 4.2.52_5
		Installing perl: 5.14.4
		Installing pcre: 8.33
		Installing libssh2: 1.4.3_1,2
		Installing ca_root_nss: 3.15.1
		Installing p5-Net-SMTP-SSL: 1.01_1
		Installing p5-Error: 0.17020
		Installing curl: 7.31.0
		Installing sqlite3: 3.7.17_1
		Installing p5-Term-ReadKey: 2.30
		Installing cvsps: 2.1_1
		Installing cscope: 15.8a
		Installing gettext: 0.18.3
		Installing libxml2: 2.8.0_2
		Installing fontconfig: 2.9.0,1
		Installing gdbm: 1.10
		Installing python27: 2.7.5_1
		Installing vim-lite: 7.3.1314_2
		Installing libxcb: 1.9.1
		Installing libX11: 1.6.0,1
		Installing apr: 1.4.8.1.5.2
		Installing apache22-worker-mpm: 2.2.25
		Installing libXrender: 0.9.8
		Installing libXft: 2.3.1
		Installing serf: 1.2.1_1
		Installing subversion: 1.8.0_3
		Installing p5-subversion: 1.8.0_3
		Installing tk: 8.5.14_1
		Installing git: 1.8.3.3_1
		Installing local-dev-meta: 20130719

	The installation will require 433 MB more space

	53 MB to be downloaded

	Proceed with installing packages [y/N]: y
	...

Only 2 packages were directly installed, so only those 2 show as non-automatic and will not be removed by `pkg autoremove`:

	dev# pkg query -e '%a = 0' '%o
	ports-mgmt/pkg
	local/dev-meta

This simplifies maintenance of the server and ensures all servers using this meta package will have the same packages installed on them. When needing to add or remove a dependency from the meta package, just update the _/usr/ports/local/dev-meta/Makefile_ on the build server, bump the *PORTREVISION* or *PORTVERSION* and then rebuild with `poudriere bulk`. Once that is completed, run `pkg upgrade` and `pkg autoremove` on the target servers. This will install new dependencies, upgrading existing, and then remove any that are no longer needed on on that server.
