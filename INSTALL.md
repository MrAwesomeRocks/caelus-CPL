# Installing CPL

The [documentation](http://caelus.readthedocs.io/en/latest) and [installation instructions](http://caelus.readthedocs.io/en/latest/user/installation.html) are quite good, however, here is a summary of all that is needed to setup CPL.

1. Download Python:
   <details><summary>Windows</summary>

   Go to the [Python website](https://python.org/) and download the latest version of Python.

   </details>

   <details><summary>MacOS and Linux</summary>

   MacOS and Linux already come with Python (as `python3`), however, you can always download a newer version from the [Python website](https://python.org/).

   </details>

2. Install [virtualenv](https://virtualenv.pypa.io/en/latest/) and [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/):
   <details><summary>Windows</summary>

   ```ps
   $> pip install virtualenv; `
        git clone https://github.com/regisf/virtualenvwrapper-powershell.git; `
        cd virtualenvwrapper-powershell; `
        ./Install.ps1; `
        cd ..; `
        Remove-Item -Recurse -Force virtualenvwrapper-powershell
   ```

   </details>

   <details><summary>MacOS and Linux</summary>

   ```sh
   $> pip3 install virtualenv virtualenvwrapper \
        && echo "source /usr/local/bin/virtualenvwrapper.sh" >> .bashrc
   ```

    </details>

3. Set the `WORKON_HOME` environment variable to `$HOME/.envs` or `%USERPROFILE%\.envs` to give the virtualenvs a consistent location. This is optional, but highly recommended. You also may want to set `VIRTUALENVWRAPPER_WORKON_CD` to `0` so that `virtualenvwrapper` doesn't change your directory when activating virtualenvs.

4. Clone the CPL source:
   ```sh
   $> git clone https://github.com/MrAwesomeRocks/caelus-CPL.git
   $> cd caelus-CPL
   ```
5. Create a CPL virtual environment:
   ```sh
   $> mkvirtualenv -a $(pwd) -r requirements.txt cpl
   ```
6. Activate the virtual environment and install CPL:
   ```sh
   $> workon cpl
   $> pip install .  # -e if you plan on making changes to CPL, pip3 if not on Windows
   ```
7. Test CPL installation:
    ```sh
    # In current terminal
    $> caelus -h

    # In a new terminal
    $> workon cpl
    $> caelus -h
    ```
