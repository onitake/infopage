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

For easy installation, a self-contained Docker script is provided.

infopage is written in Python and requires PostgreSQL, Apache,
mod_python and a handful of Python modules.

Installation steps:

1. (optional) Create a Debian base Docker image - see
   https://wiki.debian.org/Cloud/CreateDockerImage for details.
   If you skip this step, the image will be fetched from docker.io.
2. Copy `infopage.conf.example` to `infopage.conf` and fill in
   your sched.org API key and secret. You can also change the database
   settings, but in that case, you need to update them in Dockerfile
   as well.
3. Copy any customization for the page into `customize/`. For example,
   you can add the file `override.css` to change the style sheet,
   or add your own logo.png.
4. Deploy the infopage docker image: ```docker build -t infopage .```
   (don't forget the dot at the end)
5. The installation will take some time, grab a cup of tea meanwhile.
6. Start the Docker image: ```docker run -p 22 -p 80 -t -i infopage```
7. Find out what the internal IP address of the Docker container is
   and open an SSH session into it.
   For example: ```ssh root@172.17.0.2```
   The password is configured in the Dockerfile, and "infopage2016"
   by default.
8. Run the sched.org import script to get the current list of events
   and venues: ```./sched.py```
9. Display the venue list with  ```./sched.py -l```, then change it
   with:  ```./sched.py -s=-1,123,567,999``` - the numbers should
   correspond with the venue IDs. -1 is the "Happening right now" slide.

Open a web browser and point it to 172.17.0.2 (or whatever the
IP address of the Docker container is). The slideshow should start.

To Do
-----

There is currently no way to change any settings, except by connecting
directly to the database.

For example, to change the title text on the "Happening right now" slide
(don't forget to use the correct IP address and password):

```
$ ssh root@172.17.0.2
root@172.17.0.2's password: 
# psql infopage infopage
infopage=> update config set value='Happening right now' where key='now_master_text';
infopage=> \q
```

Logging does not work at the moment due to Docker's peculiar inner
workings. Use the host syslog, maybe.

The application requires quite a big setup. Since the data source
does not change very often, a much simpler server stack could be
used, like an in-memory database and statically generated content
files. They only need to be updated once per minute.
