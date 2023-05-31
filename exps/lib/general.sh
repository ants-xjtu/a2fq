# Author: Guangyu Peng (gypeng2021@163.com)
#
# Define some general functions used in experiment scrips.

#####################################
# Output error message to STDERR
# Globals:
#   None
# Arguments:
#   $@: error message(s)
# Returns:
#   None
######################################
err() {
  echo "[$(date +'%Y-%m-%d_%H:%M:%S%z')]: $@" >&2
}

#####################################
# Echo if arg $1 is Nonnegtive integer.
# Globals:
#   None
# Arguments:
#   $1: string
# Returns:
#   echo "Y" if true, "N" otherwise
######################################
is_nonnegative() {
  if [ -n "$1" -a "$1" = "${1//[^0-9]/}" ]; then
    echo "Y"
  else
    echo "N"
  fi
}

#########################################################
# Divide integer N into x parts as uniformly as possible,
# each of the x parts is an integer, echo the ith integer.
# Globals:
#   None
# Arguments:
#   $1: N, positive integer
#   $2: x, positive integer
#   $3: i, positive integer, 1 <= i <= x
# Returns:
#   echo the ith integer.
#########################################################
uniform_allocate() {
  part=$[$1 / $2]
  remain=$[$1 - $2 * part]
  if [ $[$3] -le $[remain] ]; then
    part=$[part+1]
  fi
  echo ${part}
}