import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/test-utils';
import { GroupSidebar } from '@/components/groups/GroupSidebar';
import type { Group } from '@/api/groups';

const mockGroups: Group[] = [
  { id: '1', name: 'Fiction', created_at: '2024-01-01', updated_at: '2024-01-01' },
  { id: '2', name: 'Science', created_at: '2024-01-02', updated_at: '2024-01-02' },
];

const mockUseGroups = vi.fn();
const mockMutate = vi.fn();

vi.mock('@/api/groups', () => ({
  useGroups: () => mockUseGroups(),
  useCreateGroup: () => ({ mutate: mockMutate, isPending: false }),
  useUpdateGroup: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteGroup: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock('@/components/groups/GroupFormDialog', () => ({
  GroupFormDialog: () => null,
}));

describe('GroupSidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders "No groups yet" when groups list is empty', () => {
    mockUseGroups.mockReturnValue({ data: [], isLoading: false });

    renderWithProviders(
      <GroupSidebar selectedGroupId={null} onSelectGroup={vi.fn()} />,
    );

    expect(screen.getByText('No groups yet')).toBeInTheDocument();
  });

  it('renders group names when groups exist', () => {
    mockUseGroups.mockReturnValue({ data: mockGroups, isLoading: false });

    renderWithProviders(
      <GroupSidebar selectedGroupId={null} onSelectGroup={vi.fn()} />,
    );

    expect(screen.getByText('Fiction')).toBeInTheDocument();
    expect(screen.getByText('Science')).toBeInTheDocument();
  });

  it('calls onSelectGroup when a group is clicked', async () => {
    mockUseGroups.mockReturnValue({ data: mockGroups, isLoading: false });
    const onSelectGroup = vi.fn();
    const user = userEvent.setup();

    renderWithProviders(
      <GroupSidebar selectedGroupId={null} onSelectGroup={onSelectGroup} />,
    );

    await user.click(screen.getByText('Fiction'));
    expect(onSelectGroup).toHaveBeenCalledWith('1');
  });

  it('shows "New Group" button', () => {
    mockUseGroups.mockReturnValue({ data: [], isLoading: false });

    renderWithProviders(
      <GroupSidebar selectedGroupId={null} onSelectGroup={vi.fn()} />,
    );

    expect(screen.getByRole('button', { name: 'New Group' })).toBeInTheDocument();
  });

  it('shows loading state', () => {
    mockUseGroups.mockReturnValue({ data: [], isLoading: true });

    renderWithProviders(
      <GroupSidebar selectedGroupId={null} onSelectGroup={vi.fn()} />,
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});
