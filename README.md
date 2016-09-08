infopage
========

Introduction
------------

infopage is a web site based digital signage presentation
tool with integration for sched.org.

Event data is fetched into a local database, serving
as the data source for a dynamically generated slide show.

Copyright
---------

infopage is (c) 2014-2016 Gregor Riepl <onitake@gmail.com>
All rights reserved.

Scripts, documentation and example content are released
under the simplified BSD license.
Please see the LICENSE file for details.

Installation
------------

infopage is written in Python and requires PostgreSQL, Apache,
mod_python and a handful of Python modules.

For easy installation, a self-contained Docker script is provided.

While it is possible to deploy a Docker image directly from the
source code repository, it is highly  recommended that you clone it
first and apply customizations before you run `docker build`.

Installation steps:

1.  (optional) Generate the debian base image - see
    https://wiki.debian.org/Cloud/CreateDockerImage for details.
    If you skip this step, the image will be fetched from docker.io.
2.  Clone the repository:
    ```
    git clone https://github.com/onitake/infopage
    ```
3.  Create a local branch for customizations:
    ```
    git checkout -b customize
    ```
4.  Change the SSH password in the Dockerfile.
5.  Edit infopage.conf and insert you sched.org event name and API key.
    You can also change the database settings, but in that case, you
    need to update them in Dockerfile as well.
6.  Copy any customization for the page into `customize/`. For example,
    you can add the file `override.css` to change the style sheet,
    or add your own logo.png.
7.  Deploy the infopage docker image (don't forget the dot at the end):
    ```
    docker build -t infopage .
    ```
8.  The installation will take some time, grab a cup of tea meanwhile.
9.  Start the Docker image:
    ```
    docker run -p 22:2222 -p 80:8080 -t -i infopage
    ```
10. SSH into the container:
    ```
    ssh -p 2222 -l root localhost
    ```
11. Run the sched.org import script to get the current list of events
    and venues:
    ```
    /root/sched.py
    ```
12.  Display the venue list:
    ```
    /root/sched.py -l
    ```
    and change it:
    ```
    /root/sched.py -s=-1,123,567,999
    ```
    The numbers correspond to the venue IDs and -1 is the
    "Happening right now" slide.
13.  Open a web browser and point it to the web server:
    [http://localhost:8080](http://localhost:8080)
14. Once you're satisfied, add a port forwarding for port
    80, so the webserver can be reached easily.
    Alternatively, commit and run the Docker image with a direct
    port mapping. (-p 80)
15. At this point, you should also commit all changes
    to your customize branch.

To Do
-----

There is currently no way to change any settings, except by connecting
directly to the database.

For example, to change the title text on the "Happening right now" slide
(don't forget to use the correct IP address and password):

```
$ ssh -p 2222 -l root localhost
root's password: 
# psql infopage infopage
infopage=> update config set value='Happening right now' where key='now_master_text';
infopage=> \q
```

Logging does not work at the moment due to Docker's peculiar inner
workings. Use the host syslog, maybe.

The server stack could be greatly simplified.
A more light-weight web server, a key-value store and perhaps
statically generated pages should be sufficient.

The database does not need to be updated very often (every 10
minutes or so), and the content pages only change every minute,
when the clock ticks.
