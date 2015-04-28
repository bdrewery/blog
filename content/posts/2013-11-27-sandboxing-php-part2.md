title: Sandboxing PHP part 2
date: 2013-11-27
tags: [FreeBSD,PHP,nginx,jails,shared-hosting,security,tech]

The best way to sandbox a web application is in a FreeBSD jail. Taking this a step further and placing a caching nginx reverse proxy in front of it can increase performance. The backend application server does not need to be on the same server as the internet-facing application server.
<!--more-->

A typical setup is:

                     WAN
                      ^
                      |
                   1.2.3.4
                   10.50.1.2
            +---------+-----------+
            | Frontend server     |
            |---------------------|
            | nginx reverse proxy |
            +----------+----------+
                       |
                      LAN
                       |
    +------------------+---------------------+
    |           Application server           |
    |----------------------------------------|
    |     10.50.2.2         10.50.3.2        |
    |  +---------------+ +----------------+  |
    |  |  Jail: Blog   | |  Jail: Webmail |  |
    |  |---------------| |----------------|  |
    |  |  php-fpm      | |  php-fpm       |  |
    |  |  nginx        | |  nginx         |  |
    |  +---------------+ +----------------+  |
    +----------------------------------------+

This setup allows having the frontend server cache static content to lessen the load on the backend application servers and avoids loading content dynamically through the scripting or CGI interfaces. It also allows segregation for the application servers from the WAN. Each jail can optionally be given WAN access or can be kept as LAN only.

The frontend server and backend application server can be combined if wanted:

                      WAN
                       ^
                       |
    +------------------+---------------------+
    |           Application server           |
    |----------------------------------------|
    |        +---------+-----------+         |
    |        | nginx reverse proxy |         |
    |        +---------+-----------+         |
    |                 / \                    |
    |     10.50.2.2         10.50.3.2        |
    |  +---------------+ +----------------+  |
    |  |  Jail: Blog   | |  Jail: Webmail |  |
    |  |---------------| |----------------|  |
    |  |  php-fpm      | |  php-fpm       |  |
    |  |  nginx        | |  nginx         |  |
    |  +---------------+ +----------------+  |
    +----------------------------------------+

## Reverse proxy / Frontend server

The frontend server is the only one that needs WAN access. It will only need nginx installed which will forward all requests to the backend application servers. A typical configuration for the reverse proxy is:

```nginx
# /usr/local/etc/nginx/vhosts/blog.example.com

server {
    listen       1.2.3.4:80;
    server_name  blog.example.com;

    # Cache all static content for 2 days
    location ~* ^.+.(jpg|jpeg|gif|png|ico|css|zip|tgz|gz|rar|bz2|doc|xls|exe|pdf|ppt|txt|tar|mid|midi|wav|bmp|rtf|js)$ {
        proxy_cache_valid 200 201 302 120m;
        expires 2d;
        proxy_pass http://10.50.2.2:80;
        proxy_cache one;
    }

    location / {
        proxy_pass http://10.50.2.2:80;
        proxy_read_timeout 40;
    }
}
```

This will forward all requests to the backend server for _blog.example.com_ on _10.50.1.2_. It will also cache all static content on the frontend server for 2 days which will lessen the load on the backend application server.

## Application Server

Each application that needs to be setup will have its own jail and its own nginx process inside of that jail if needed. Some applications have their own network daemons that will not require using nginx for FastCGI.

First the jail IPs need to be added to the host. Add them to the interface's address list in _/etc/rc.conf_:

    :::shell
    # /etc/rc.conf
    ipv4_addrs_em0="10.50.2.2/24 10.50.3.2/24"

Then restart networking:

    :::shell-session
    root@host# service netif restart && service routing restart

### Jail setup

The [sysutils/ezjail](http://www.freshports.org/sysutils/ezjail) port is the easiest utility for setting up the jail on FreeBSD. The jail needs to be created from the host and then populated with packages from inside of the jail. More details for this can be found on the [ezjail website](http://erdgeist.org/arts/software/ezjail/).

    :::shell-session
    # Create the base jail
    root@host# ezjail-admin update -i

    # Create each application jail
    root@host# ezjail-admin create -c zfs -r /tank/jails/blog blog 10.50.2.2
    root@host# ezjail-admin create -c zfs -r /tank/jails/webmail webmail 10.50.3.2

    # Start the jails
    root@host# ezjail-admin start blog
    root@host# ezjail-admin start webmail

    # Enable ezjail for next boot
    root@host# echo ezjail_enable=YES >> /etc/rc.conf

Next packages can be installed using [pkg](http://www.freebsd.org/doc/handbook/pkgng-intro.html) from the host system. This assumes that meta packages have been setup on the remote repository as described in [managing FreeBSD servers with meta packages](/posts/2013-07-21-managing-role-based-freebsd-servers-with-meta-packages-and-poudriere). This also assumes that the meta package includes all needed dependencies including [www/nginx](http://www.freshports.org/www/nginx).

    ::shell-session
    root@host# pkg -j blog install local/blog
    root@host# pkg -j webmail install local/webmail

### Application setup

Enter the jail from the host with `ezjail-admin console blog`. From there nginx, PHP-FPM and the application can all be setup.

This example assumes that [PHP-FPM](http://php-fpm.org/) will be used with a PHP application.

#### nginx

nginx needs to be setup to use FastCGI.

```nginx
# /usr/local/etc/nginx/vhosts/blog.example.com
server {
    listen       10.50.2.2:80;
    server_name  blog.example.com;

    location / {
        alias /usr/local/www/blog/;
        index index.php index.html index.htm;
        break;
    }

    location ~ /(.*\.php)$ {
        root /usr/local/www/blog/;

        # Filter out arbitrary code execution
        try_files $uri = 404;
        location ~ \..*/.*\.php$ {return 404;}

        fastcgi_pass   unix:/var/run/php-fpm-www.sock;
        include        fastcgi_params;
        break;
    }
}
```
```nginx
# /usr/local/etc/nginx/fastcgi_params
fastcgi_index  index.php;

fastcgi_connect_timeout 60;
fastcgi_send_timeout 180;
fastcgi_read_timeout 180;
fastcgi_buffer_size 128k;
fastcgi_buffers 4 256k;
fastcgi_busy_buffers_size 256k;
fastcgi_temp_file_write_size 256k;
fastcgi_intercept_errors on;

fastcgi_param  PATH_INFO          $fastcgi_path_info;
fastcgi_param  PATH_TRANSLATED    $document_root$fastcgi_path_info;

fastcgi_param  QUERY_STRING       $query_string;
fastcgi_param  REQUEST_METHOD     $request_method;
fastcgi_param  CONTENT_TYPE       $content_type;
fastcgi_param  CONTENT_LENGTH     $content_length;

fastcgi_param  SCRIPT_NAME        $fastcgi_script_name;
fastcgi_param  SCRIPT_FILENAME    $document_root$fastcgi_script_name;
fastcgi_param  REQUEST_URI        $request_uri;
fastcgi_param  DOCUMENT_URI       $document_uri;
fastcgi_param  DOCUMENT_ROOT      $document_root;
fastcgi_param  SERVER_PROTOCOL    $server_protocol;

fastcgi_param  GATEWAY_INTERFACE  CGI/1.1;
fastcgi_param  SERVER_SOFTWARE    nginx/$nginx_version;

fastcgi_param  REMOTE_ADDR        $remote_addr;
fastcgi_param  REMOTE_PORT        $remote_port;
fastcgi_param  SERVER_ADDR        $server_addr;
fastcgi_param  SERVER_PORT        $server_port;
fastcgi_param  SERVER_NAME        $server_name;

# PHP only, required if PHP was built with --enable-force-cgi-redirect
fastcgi_param  REDIRECT_STATUS    200;
```

```shell
# /etc/rc.conf
nginx_enable=YES
```

Start nginx with `service nginx start`.

#### PHP-FPM

PHP-FPM will start a daemon to listen for local connections from nginx. All that needs to be done for PHP-FPM is to configure it to listen on a UNIX socket and to enable it on boot.

```ini
# /usr/local/etc/php-fpm.conf
# Replace listen lines with:
listen = /var/run/php-fpm-$pool.sock
listen.owner = www
listen.group = www
listen.mode = 0660
```

```shell
# /etc/rc.conf
php_fpm_enable=YES
```

Start PHP-FPM with `service php-fpm start`.

#### Application

Configure the application itself as needed.

## Updating jails

Occasionally the jail's package can be updated from the host:

    :::shell-session
    root@host# pkg -j blog upgrade

## Wrap up

By moving each application into its own jail, security and performance can both be improved greatly. mod\_php with Apache could be used but is much more heavyweight in each jail.
