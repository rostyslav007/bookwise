import { useState } from "react";
import { PlusIcon, MoreHorizontalIcon, PencilIcon, TrashIcon } from "lucide-react";
import {
  useGroups,
  useCreateGroup,
  useUpdateGroup,
  useDeleteGroup,
  type Group,
} from "@/api/groups";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { GroupFormDialog } from "@/components/groups/GroupFormDialog";

interface GroupSidebarProps {
  selectedGroupId: string | null;
  onSelectGroup: (groupId: string | null) => void;
}

export function GroupSidebar({ selectedGroupId, onSelectGroup }: GroupSidebarProps) {
  const { data: groups = [], isLoading } = useGroups();
  const createGroup = useCreateGroup();
  const updateGroup = useUpdateGroup();
  const deleteGroup = useDeleteGroup();

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<Group | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Group | null>(null);

  function handleCreate(name: string) {
    createGroup.mutate({ name }, {
      onSuccess: () => setCreateDialogOpen(false),
    });
  }

  function handleRename(name: string) {
    if (!renameTarget) return;
    updateGroup.mutate({ id: renameTarget.id, name }, {
      onSuccess: () => setRenameTarget(null),
    });
  }

  function handleDelete() {
    if (!deleteTarget) return;
    deleteGroup.mutate(deleteTarget.id, {
      onSuccess: () => {
        if (selectedGroupId === deleteTarget.id) {
          onSelectGroup(null);
        }
        setDeleteTarget(null);
      },
    });
  }

  return (
    <aside className="flex h-full w-64 flex-col border-r bg-muted/30">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Groups</h2>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setCreateDialogOpen(true)}
          aria-label="New Group"
        >
          <PlusIcon />
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto p-2">
        {isLoading && (
          <p className="px-2 py-4 text-center text-sm text-muted-foreground">
            Loading...
          </p>
        )}

        {!isLoading && groups.length === 0 && (
          <p className="px-2 py-4 text-center text-sm text-muted-foreground">
            No groups yet
          </p>
        )}

        <ul className="flex flex-col gap-0.5">
          {groups.map((group) => (
            <GroupItem
              key={group.id}
              group={group}
              isSelected={selectedGroupId === group.id}
              onSelect={() => onSelectGroup(group.id)}
              onRename={() => setRenameTarget(group)}
              onDelete={() => setDeleteTarget(group)}
            />
          ))}
        </ul>
      </nav>

      <GroupFormDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        title="New Group"
        description="Enter a name for the new group."
        onSubmit={handleCreate}
        isPending={createGroup.isPending}
      />

      <GroupFormDialog
        open={renameTarget !== null}
        onOpenChange={(open) => { if (!open) setRenameTarget(null); }}
        title="Rename Group"
        description="Enter a new name for the group."
        initialName={renameTarget?.name}
        onSubmit={handleRename}
        isPending={updateGroup.isPending}
      />

      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}
      >
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>Delete Group</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteTarget?.name}"? This will
              also permanently delete all books in this group, including their
              chapter structures, search indexes, and PDF files. This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteTarget(null)}
              disabled={deleteGroup.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteGroup.isPending}
            >
              {deleteGroup.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  );
}

interface GroupItemProps {
  group: Group;
  isSelected: boolean;
  onSelect: () => void;
  onRename: () => void;
  onDelete: () => void;
}

function GroupItem({ group, isSelected, onSelect, onRename, onDelete }: GroupItemProps) {
  return (
    <li
      className={`group flex items-center justify-between rounded-md px-2 py-1.5 text-sm cursor-pointer transition-colors ${
        isSelected
          ? "bg-accent text-accent-foreground"
          : "hover:bg-accent/50"
      }`}
      onClick={onSelect}
    >
      <span className="truncate">{group.name}</span>

      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              variant="ghost"
              size="icon-xs"
              className="opacity-0 group-hover:opacity-100 data-popup-open:opacity-100"
              onClick={(e) => e.stopPropagation()}
              aria-label={`Actions for ${group.name}`}
            />
          }
        >
          <MoreHorizontalIcon />
        </DropdownMenuTrigger>

        <DropdownMenuContent align="end" side="bottom">
          <DropdownMenuItem
            onClick={(e) => {
              e.stopPropagation();
              onRename();
            }}
          >
            <PencilIcon />
            Rename
          </DropdownMenuItem>
          <DropdownMenuItem
            variant="destructive"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
          >
            <TrashIcon />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  );
}
