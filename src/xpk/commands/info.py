"""
Copyright 2024 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from ..utils import  xpk_exit, xpk_print
from ..core.kueue import verify_kueuectl_installation
from .cluster import set_cluster_command
from ..core.commands import (
    run_command_for_value,
)
from ..core.core import (
    add_zone_and_project,
)
import json
from tabulate import tabulate

table_fmt = 'github'

def prepare_kueuectl(args) -> int:
  """Verify if kueuectl is installed. If not install kueuectl.
  Args:
    args: user provided arguments.
  Returns:
    0 if succesful and 1 otherwise.
  """
  xpk_print('Veryfing kueuectl installation')
  args.dry_run = False
  verify_kueuectl_installed_code = verify_kueuectl_installation(args)
  if verify_kueuectl_installed_code == 0:
    xpk_print('kueuectl installed')
    return 0

  if verify_kueuectl_installed_code != 0:
    xpk_print('kueuectl not installed. Please follow https://kueue.sigs.k8s.io/docs/reference/kubectl-kueue/installation/ to install kueuectl.')
    return verify_kueuectl_installed_code

def info(args) -> None:
  """Function around list localqueue.

  Args:
    args: user provided arguments for running the command.
  Returns:
    0 if successful and 1 otherwise.
  """
  add_zone_and_project(args)

  shared_flags_error = apply_shared_flags(args)
  if shared_flags_error != 0:
    xpk_exit(shared_flags_error)

  set_cluster_command_code = set_cluster_command(args)
  if set_cluster_command_code != 0:
    xpk_exit(set_cluster_command_code)

  installation_code = prepare_kueuectl(args)
  if installation_code != 0:
    xpk_exit(installation_code)

  lq_code, lqs = run_kueuectl_list_localqueue(args)
  if lq_code != 0:
    xpk_exit(lq_code)

  cq_code, cqs = run_kueuectl_list_clusterqueue(args)
  if cq_code != 0:
    xpk_exit(cq_code)

  aggregate_results(cqs, lqs)
  return

def apply_shared_flags(args) -> tuple[int, str]:
  """Apply shared flags. It checks --project and --zone
    flags and executes proper gcloud commands if present.
  
  Args:
    args: user provided args.
  
  Returns:
    0 if successful and 1 otherwise.
  """
  if args.project is not None:
    project_cmd = f'gcloud config set project {args.project}'
    return_code, _ = run_command_for_value(project_cmd, 'Set gcp project', args)
    if return_code != 0:
      xpk_exit(return_code)

  if args.zone is not None:
    zone_cmd = f'gcloud config set compute/zone {args.zone}'
    return_code, _ =run_command_for_value(zone_cmd, 'set gcloud zone', args)
    if return_code != 0:
      xpk_exit(return_code)
  
  return 0

def aggregate_results(cqs, lqs) :
  """Aggregate listed clusterqueues and localqueues with resource usage and print them as table.
  
  Args:
    lqs: list of localqueues.
    cqs: list of clusterqueues.
  
  """
  cq_list = json.loads(cqs)['items']
  lq_list = json.loads(lqs)['items']

  cq_res, cq_usage = parse_queue_lists(cq_list, usage_key='flavorsUsage')
  lq_res, lq_usage = parse_queue_lists(lq_list)
  
  xpk_print('Cluster Queue Flavors reservations: \n', tabulate(cq_res, headers = 'keys', tablefmt=table_fmt))
  xpk_print('Cluster Queue Flavors usage: \n', tabulate(cq_usage, headers = 'keys', tablefmt=table_fmt))

  xpk_print('Local Queue Flavors reservations: \n', tabulate(lq_res, headers = 'keys', tablefmt=table_fmt))
  xpk_print('Local Queue Flavors usage: \n', tabulate(lq_usage, headers = 'keys', tablefmt=table_fmt))

def parse_queue_lists(qs, usage_key = 'flavorUsage',
  reservation_key = 'flavorsReservation') -> tuple[list[dict], list[dict]]:
  q_res, q_usage = [], []
  for q in qs:
    q_res = get_flavors_status_field(q, reservation_key)
    q_usage = get_flavors_status_field(q, usage_key)
  return q_res, q_usage

def get_flavors_status_field(q_entry, statusField) -> list[dict]:
  """Parse q_entry to retrieve list of flavors usage or reservation

  Args:
    q_entry - single entry into either LocalQueue or ClusterQueue structured as json
    statusField - either "flavorsReservation" or "flavorsUsage"
  Returns:
    list of dicts where each contains fields: queueName, flavorName, resource, total
  """
  status = q_entry['status']
  flavors_res = status[statusField]

  reservations = []

  for flavor in flavors_res:
    name = flavor['name']
    for res in flavor['resources']:
      reservations.append({
        'queueName': q_entry['metadata']['name'],
        'flavorName': name,
        'resource': res['name'],
        'total': res['total'],
      })
  return reservations

def run_kueuectl_list_localqueue(args) -> tuple[int, str]:
  """Run the kueuectl list localqueue command.

  Args:
    args: user provided arguments for running the command.

  Returns:
    0 if successful and 1 otherwise.
  """
  command = (
      'kubectl kueue list localqueue -o json'
  )
  return_code, val = run_command_for_value(command, 'list localqueue', args)

  if return_code != 0:
    xpk_print(f'Cluster info request returned ERROR {return_code}')
    return 1, ''
  return 0, val


def run_kueuectl_list_clusterqueue(args) -> int:
  """Run the kueuectl list clusterqueue command.

  Args:
    args: user provided arguments for running the command.

  Returns:
    0 if successful and 1 otherwise.
  """
  command = (
      'kubectl kueue list clusterqueue -o json'
  )
  return_code, val = run_command_for_value(command, 'list clusterqueue', args)

  if return_code != 0:
    xpk_print(f'Cluster info request returned ERROR {return_code}')
    return 1, ''
  return 0, val