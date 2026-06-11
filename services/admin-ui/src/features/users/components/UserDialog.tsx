/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SearchableSelect, SelectOption } from '@/components/ui/searchable-select';
import { User } from '@/services/api/tesaApi';
import { Shield, UserCog, Eye, Palette } from 'lucide-react';

interface UserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user?: User | null;
  onSave: (user: Partial<User>) => void;
}

export const UserDialog: React.FC<UserDialogProps> = ({
  open,
  onOpenChange,
  user,
  onSave,
}) => {
  const [formData, setFormData] = React.useState({
    name: '',
    email: '',
    role: 'viewer' as User['role'],
  });

  React.useEffect(() => {
    if (user) {
      setFormData({
        name: user.name,
        email: user.email,
        role: user.role,
      });
    } else {
      setFormData({
        name: '',
        email: '',
        role: 'viewer',
      });
    }
  }, [user]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{user ? 'Edit User' : 'Add New User'}</DialogTitle>
          <DialogDescription>
            {user ? 'Update user information' : 'Create a new user account'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
          </div>
          <div>
            <Label htmlFor="role">Role</Label>
            <SearchableSelect
              options={[
                { 
                  value: 'organization_admin', 
                  label: 'Organization Admin',
                  description: 'Full control over organization and sub-organizations',
                  icon: <Shield className="h-4 w-4 text-purple-500" />
                },
                { 
                  value: 'admin', 
                  label: 'Admin',
                  description: 'Department/team administration within organization',
                  icon: <Shield className="h-4 w-4 text-red-500" />
                },
                {
                  value: 'operator',
                  label: 'Operator',
                  description: 'Device management and monitoring',
                  icon: <UserCog className="h-4 w-4 text-blue-500" />
                },
                {
                  value: 'product_industrial_designer',
                  label: 'Product Model Designer',
                  description: 'Upload and manage 3D product models',
                  icon: <Palette className="h-4 w-4 text-pink-500" />
                },
                {
                  value: 'viewer',
                  label: 'Viewer',
                  description: 'Read-only access to data and reports',
                  icon: <Eye className="h-4 w-4 text-gray-500" />
                }
              ]}
              value={formData.role}
              onValueChange={(value) =>
                setFormData({ ...formData, role: value as User['role'] })
              }
              placeholder="Select user role"
              searchable={false}
              size="md"
              aria-label="User Role"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">
              {user ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
