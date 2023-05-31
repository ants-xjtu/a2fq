# Author: Guangyu Peng (gypeng2021@163.com)
#
# Define functions related to dumbbell topology.

#####################################
# Echo ip of the ith client in dumbbell topology.
# Globals:
#   None
# Arguments:
#   $1: integer within [1, 250], representing the ith client
# Returns:
#   None
######################################
dumbbell::client_ip() {
  echo "10.0.${1}.${1}"
}

#####################################
# Echo ip of the ith server in dumbbell topology.
# Globals:
#   None
# Arguments:
#   $1: integer within [1, 250], representing the ith server
# Returns:
#   None
######################################
dumbbell::server_ip() {
  echo "10.1.${1}.${1}"
}