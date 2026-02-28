# SAM deploy policy (for bedrock-app)

The deploy failed because the IAM user needs **`iam:TagRole`** (and **`iam:UntagRole`**) so CloudFormation can tag the Lambda role.

**Fix:** Edit your **SAM@policy** in IAM and add these actions to the IAM statement:

In the **IAM** block of your policy, add:

- `iam:TagRole`
- `iam:UntagRole`

So the IAM part should look like:

```json
{
  "Effect": "Allow",
  "Action": [
    "iam:CreateRole",
    "iam:DeleteRole",
    "iam:GetRole",
    "iam:PassRole",
    "iam:AttachRolePolicy",
    "iam:DetachRolePolicy",
    "iam:PutRolePolicy",
    "iam:DeleteRolePolicy",
    "iam:TagRole",
    "iam:UntagRole"
  ],
  "Resource": "*"
}
```

**Steps in AWS:**

1. IAM → **Policies** → search **SAM@policy** → click it.
2. **Edit** (or "Edit policy").
3. Open the **JSON** tab.
4. In the statement that has `"Action": [ "iam:CreateRole", ... ]`, add `"iam:TagRole"` and `"iam:UntagRole"` to that list.
5. **Save changes**.

Then run again: `./deploy.sh`
