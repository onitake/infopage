# Get Debian stable (preferably from a local image)
FROM debian

# (c) 2016
MAINTAINER Gregor Riepl <onitake@gmail.com>

# Install required software: Apache, mod_python, PostgreSQL, OpenSSH, supervisord and a few required Python modules
RUN apt-get update && apt-get install -y locales python python-psycopg2 python-requests python-lxml postgresql-9.4 postgresql-client apache2 libapache2-mod-python openssh-server supervisor

# Set the correct timezone and locale (we need a UTF-8 locale or we will run into problems later),
# then enable UTF-8 in the Postgres client library
RUN echo "Europe/Zurich" > /etc/timezone && dpkg-reconfigure -f noninteractive tzdata
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && echo 'LANG="en_US.UTF-8"' > /etc/default/locale && dpkg-reconfigure -f noninteractive locales && update-locale LANG=en_US.UTF-8
RUN sed -i 's/#client_encoding = sql_ascii/client_encoding = utf8/' /etc/postgresql/9.4/main/postgresql.conf

# Create some space for log and pid files
RUN mkdir -p /var/lock/apache2 /var/run/apache2 /var/run/sshd /var/log/supervisor

# Set up login credentials
RUN echo 'root:infopage2016' | chpasswd
RUN sed -i 's/PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config
# To simplify things, Postgres is on a local-no-password setup
RUN sed -i 's/local  *all  *all  *peer/local all all trust/' /etc/postgresql/9.4/main/pg_hba.conf

# Install and configure the web share and database update scripts
COPY infopage.conf /etc/infopage.conf
COPY infopage/* /var/www/html/
COPY infopage.py /var/www/html/
COPY customize/* /var/www/html/
COPY ["sched.py", "schema.py", "infopage.py", "/root/"]
RUN ["chmod", "755", "/root/sched.py", "/root/schema.py"]
COPY python-handler.conf /etc/apache2/conf-available/
RUN ["a2enconf", "python-handler"]

# Set up database and access, and create the initial schema
# Don't use USER for this - schema.py needs to be somewhere to make it executable as non-root
RUN /etc/init.d/postgresql start && su -c 'psql -c "CREATE USER infopage;"' postgres && su -c 'psql -c "CREATE DATABASE infopage;"' postgres && su -c 'psql -c "GRANT ALL PRIVILEGES ON DATABASE infopage TO infopage;"' postgres && /root/schema.py -d

# Create a cron job for the database update script
# Will be installed later when cron is running
COPY sched.cron /root/

# Install daemon manager config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Mount shared volumes for logs and database
VOLUME  ["/var/log/postgresql", "/var/lib/postgresql", "/var/log/supervisor", "/var/log/apache2"]

# Enable outside access to SSH and web
EXPOSE 22 80

# Launch the whole thing
CMD ["/usr/bin/supervisord"]
