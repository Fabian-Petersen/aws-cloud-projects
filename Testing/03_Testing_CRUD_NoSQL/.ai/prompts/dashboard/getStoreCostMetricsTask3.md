# Problem

The discrepancy is confirmed and comes from different ownership definitions:

- /api/jobs/completed means “jobs completed by James” and filters actions using action_sub == James’s sub.
- Maintenance Cost means “jobs assigned to James” and filters requests using assign_to_sub == James’s sub, then joins actions using action.request_id == request.id.

# Finding

Live data for James’s five completed actions:
Job card Actioned by Currently assigned to Cost metric
Job-CTS-202610-0001 James May James May Included
Job-VTR-202608-0005 James May Leon Mathlay Excluded
Job-DCN-202609-0001 James May Leon Mathlay Excluded
Job-VTR-202608-0003 James May Leon Mathlay Excluded
Job-GAC-202610-0003 James May Leon Mathlay Excluded

James currently has a second assigned request, Job-GAC-202610-0004, but its referenced action ID does not exist in the maintenance-action table. Consequently, it contributes no job or cost.
Therefore:
Completed by James: 5
Of those assigned to James: 1
Additional assigned request: 1, but its linked action is missing

Maintenance Cost jobs: 1
Relevant implementation:

- Completed route filters action_sub: [getJobsCompletedList.py (line 119)](C:/Users/user/Documents/Atlantic Meat/backend/aws-cloud-projects/Testing/03_Testing_CRUD_NoSQL/lambdas/jobs/getJobsCompletedList/getJobsCompletedList.py:119)
- Cost metrics filter assign_to_sub and join through request_id: [getStoreCostMetrics.py (line 195)](C:/Users/user/Documents/Atlantic Meat/backend/aws-cloud-projects/Testing/03_Testing_CRUD_NoSQL/lambdas/dashboard/getStoreCostMetrics/getStoreCostMetrics.py:195)
- action_sub is captured from the authenticated person completing the job: [postJobAction.py (line 323)](C:/Users/user/Documents/Atlantic Meat/backend/aws-cloud-projects/Testing/03_Testing_CRUD_NoSQL/lambdas/jobs/postJobAction/postJobAction.py:323)
- assign_to_sub is stored separately on the request: [postApproveRequest.py (line 495)](C:/Users/user/Documents/Atlantic Meat/backend/aws-cloud-projects/Testing/03_Testing_CRUD_NoSQL/lambdas/jobs/postApproveRequest/postApproveRequest.py:495)
  This is consistent with the earlier Task 2 requirement that technician Maintenance Cost must be based on assignment, not who completed the action. Matching the completed route’s five jobs would require changing that business rule to action_sub, which would conflict with Task 2.

No files or live AWS data were changed.

Task3
No, Maintenance Cost Jobs must be allocated to the technician who completed the task, same as Jobs Completed. The pending/in progress jobs can be seen by all technicians but once you completed a job it must be your jobs completed cost.

- Correct the data for getMaintenanceCostMetrics to send all jobs completed by a technician and not what was assigned.
