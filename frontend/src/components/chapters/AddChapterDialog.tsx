import { useState } from "react";
import { useCreateChapter } from "@/api/chapters";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog";
import { Plus } from "lucide-react";

interface AddChapterDialogProps {
  bookId: string;
  parentId?: string;
  triggerSize?: "sm" | "icon-xs";
}

export function AddChapterDialog({
  bookId,
  parentId,
  triggerSize = "sm",
}: AddChapterDialogProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [startPage, setStartPage] = useState(1);
  const [endPage, setEndPage] = useState(1);

  const createChapter = useCreateChapter();

  function resetForm() {
    setTitle("");
    setStartPage(1);
    setEndPage(1);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    createChapter.mutate(
      {
        bookId,
        title,
        parent_id: parentId,
        start_page: startPage,
        end_page: endPage,
      },
      {
        onSuccess: () => {
          resetForm();
          setOpen(false);
        },
      }
    );
  }

  const isIconTrigger = triggerSize === "icon-xs";

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          isIconTrigger ? (
            <Button variant="ghost" size="icon-xs">
              <Plus className="size-3" />
            </Button>
          ) : (
            <Button variant="outline" size="sm">
              <Plus className="size-3.5" />
              Add chapter
            </Button>
          )
        }
      />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {parentId ? "Add sub-chapter" : "Add chapter"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Title</label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Chapter title"
              required
              autoFocus
            />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium">
                Start page
              </label>
              <Input
                type="number"
                value={startPage}
                onChange={(e) => setStartPage(Number(e.target.value))}
                min={1}
                required
              />
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium">
                End page
              </label>
              <Input
                type="number"
                value={endPage}
                onChange={(e) => setEndPage(Number(e.target.value))}
                min={1}
                required
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>
              Cancel
            </DialogClose>
            <Button type="submit" disabled={createChapter.isPending}>
              {createChapter.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
