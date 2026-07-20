# Publication boundary

Load this reference only immediately before a persistent publication write.
Private drafting and discussion do not trigger it.

## Trust boundary

The GitHub owner of the actual destination is the default trust domain. Links
between repositories owned by that same account or organization may pass;
references to another owner do not. Destination publication authority does not
authorize disclosure of a relationship with another trust domain.

Treat cross-owner repository URLs, issue and commit autolinks, account-profile
links, rendered Markdown mentions, and identity-bearing GitHub content-host URLs
as reciprocal or compromising publication. Public output describes the
reusable task shape or failure class, not its originating external card,
repository, account, or provider.

The built-in checks cannot identify a bare repository name, SHA, customer name,
or private policy name without context. Put every known cross-domain identity
from the task, plus any sensitive same-owner sibling identity, in a temporary
patterns file, one case-insensitive literal per line. Do not include the
intended destination identity.

## Exact-byte preflight

1. Resolve `DESTINATION_REPO` from the actual GitHub write target or canonical
   remote, never from the outbound text.
2. Put each exact outbound field or file in a temporary regular file. Use those
   same bytes for the write.
3. Run `adt publication-gate --destination-repo "$DESTINATION_REPO" --input
   "$OUTBOUND_FILE" --patterns-file "$PATTERNS_FILE"` immediately before the
   write.

   Omit `--patterns-file` only when the task has no cross-domain or private
   identities beyond those covered by the built-in GitHub checks.
4. `HOLD` means rewrite or generalize. There is no autonomous cross-owner
   bypass. If an exact relationship is essential, stop and ask the owner rather
   than publishing it.
5. On success, require contract `adt.publication-gate.v1`, the actual
   destination, and the unchanged byte count and SHA-256. Any edit requires a
   new gate pass.

The receipt attests only the supplied bytes. It does not inspect or attest a
Git object graph, branch contents, refspec, or completed write. Existing
history needs separate review; never present this receipt as proof of a push.

Patterns and receipts are transient private control data, not KB, CI, or
closeout artifacts. Never publish or persist them.
