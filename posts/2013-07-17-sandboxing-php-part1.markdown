Title: Sandboxing PHP part 1
Tags: FreeBSD,PHP,nginx,jails,shared-hosting,security,tech

For additional security layers and separation, I run my web applications inside of dedicated jails. This has been an ongoing progression for me. I will layout where I started, where I progressed, and how I do it now.

## Apache+mod\_php

Originally, I would run all applications under _www_ user using apache+mod\_php. This was the classic LAMP approach and the most simple approach to hosting a web application. It is also the most insecure if you are hosting more than 1 user or application. If you are running apache as _root_ then you have effectively given root to the world.

The biggest problem with this is that every application is executing code as the user that apache is running as. So that "secure" *config.php* file with some user or application's private db credentials in can easily be read by another. This creates a very easy attack vector for taking over another site on a shared system. Just sign-up and read in the file. You now can grant yourself administrative rights on their application by connecting directly to the DB.

Even if you are not doing "shared hosting", this makes every application on your system as weak as the weakest application running under _www_.

A better approach is to create a dedicated user for every application, or to run an application under the user whos *public_html* it is in.

## Apache+suphp

An option which was mostly viable up until 2009 was suPHP. It allows executing an application using a setuid wrapper using the php-cli interface. Due to its [EoL](http://permalink.gmane.org/gmane.comp.php.suphp.general/1151) status, maintenance history, requiring setuid root, and poor performance, I would not recommend using this for new projects.

## Apache+mod_fcgi+suexec+php-cgi

The next step for me was primarily focused on improving the performance of suphp. This resulted in using mod\_fcgi to spawn a CGI process for the application and interact with that. This avoided startup overhead. It's still poor though as it requires the setuid binary and is much more complex since it involved mod\_fcgi and an extra wrapper script.

## nginx+php-fpm

This setup works very well in terms of security and performance. A separate php-fpm instance is spawned for each site. I assign each application a dedicated user. The php-fpm processes run as this user and create a CGI interface for nginx to connect to. This can be taken 1 step further with each application in its own jail, to further protect the host system. The jails are configured without WAN access; they only have LAN access and only in a small subnet dedicated for nginx to connect to the jail with.

In the next part I will cover exactly how this is setup.
