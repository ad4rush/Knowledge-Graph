"""
Student Data Organizer - GUI Version
Simple interface for organizing student LinkedIn data

Usage:
  python organize_students_gui.py
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from PIL import Image, ImageTk, ImageGrab
import threading
import shutil

class StudentOrganizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Data Organizer")
        self.root.geometry("900x720")
        self.root.configure(bg='#f0f0f0')
        
        # Directories
        self.pdf_dir = "linkedin_pdfs"
        self.text_dir = "manual_text"
        self.photo_dir = "photos"
        self.list_file = "list.txt"
        
        # Create directories
        os.makedirs(self.pdf_dir, exist_ok=True)
        os.makedirs(self.text_dir, exist_ok=True)
        os.makedirs(self.photo_dir, exist_ok=True)
        
        # Data
        self.students = []
        self.current_index = 0
        self.current_student = None
        self.missing_students = []
        
        # Setup UI
        self.setup_ui()
        self.load_students()
        
    def setup_ui(self):
        """Create the user interface"""
        # Title
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        
        title = tk.Label(title_frame, text="Student Data Organizer", 
                        font=('Arial', 20, 'bold'), bg='#2c3e50', fg='white')
        title.pack(pady=15)
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Student info section
        info_frame = tk.LabelFrame(main_frame, text="Current Student", 
                                  font=('Arial', 12, 'bold'), bg='#f0f0f0', 
                                  fg='#2c3e50', padx=10, pady=8)
        info_frame.pack(fill='x', pady=(0, 10))
        
        # Top row: student name and skip button
        top_row = tk.Frame(info_frame, bg='#f0f0f0')
        top_row.pack(fill='x')
        
        self.student_label = tk.Label(top_row, text="No student loaded", 
                                     font=('Arial', 14, 'bold'), bg='#f0f0f0',
                                     fg='#e74c3c')
        self.student_label.pack(side='left', expand=True)
        
        # Explicit save button in the top row (similar prominence to Skip Student)
        self.save_top_btn = tk.Button(top_row, text="💾 Save Student",
                          command=self.save_and_next, bg='#27ae60',
                          fg='white', font=('Arial', 9, 'bold'),
                          padx=12, pady=4, cursor='hand2')
        self.save_top_btn.pack(side='right', padx=(0, 6))

        self.skip_top_btn = tk.Button(top_row, text="⏭ Skip Student",
                         command=self.skip_student, bg='#e67e22',
                         fg='white', font=('Arial', 9, 'bold'),
                         padx=12, pady=4, cursor='hand2')
        self.skip_top_btn.pack(side='right')
        
        self.progress_label = tk.Label(info_frame, text="0/0", 
                                      font=('Arial', 10), bg='#f0f0f0',
                                      fg='#7f8c8d')
        self.progress_label.pack()
        
        # Photo section
        photo_frame = tk.LabelFrame(main_frame, text="📷 Profile Photo", 
                                   font=('Arial', 11, 'bold'), bg='#f0f0f0',
                                   fg='#2c3e50', padx=10, pady=8)
        photo_frame.pack(fill='x', pady=(0, 10))
        
        photo_btn_frame = tk.Frame(photo_frame, bg='#f0f0f0')
        photo_btn_frame.pack()
        
        self.paste_photo_btn = tk.Button(photo_btn_frame, text="📋 Paste Photo from Clipboard",
                                        command=self.paste_photo, bg='#3498db',
                                        fg='white', font=('Arial', 10, 'bold'),
                                        padx=15, pady=6, cursor='hand2')
        self.paste_photo_btn.pack(side='left', padx=5)
        
        self.skip_photo_btn = tk.Button(photo_btn_frame, text="⏭ Skip Photo",
                                       command=self.skip_photo, bg='#95a5a6',
                                       fg='white', font=('Arial', 10),
                                       padx=15, pady=6, cursor='hand2')
        self.skip_photo_btn.pack(side='left', padx=5)
        
        self.photo_status = tk.Label(photo_frame, text="", font=('Arial', 9),
                                    bg='#f0f0f0', fg='#27ae60')
        self.photo_status.pack(pady=(5, 0))
        
        # Data entry sections - No scrolling needed
        self.create_data_section(main_frame, "💼 Skills", "skills_text", height=3)
        self.create_data_section(main_frame, "🚀 Projects", "projects_text", height=4)
        self.create_data_section(main_frame, "📚 Courses", "courses_text", height=3)
        self.create_data_section(main_frame, "ℹ️ Other Information", "other_text", height=3)
        
        # Action buttons
        action_frame = tk.Frame(self.root, bg='#f0f0f0')
        action_frame.pack(fill='x', padx=20, pady=(10, 20))
        
        self.save_btn = tk.Button(action_frame, text="💾 Save & Next Student",
                                 command=self.save_and_next, bg='#27ae60',
                                 fg='white', font=('Arial', 12, 'bold'),
                                 padx=20, pady=10, cursor='hand2')
        self.save_btn.pack(side='left', padx=5)

        # Save-only button (save current student without advancing)
        self.save_only_btn = tk.Button(action_frame, text="💾 Save",
                           command=self.save_current, bg='#2ecc71',
                           fg='white', font=('Arial', 12, 'bold'),
                           padx=12, pady=10, cursor='hand2')
        self.save_only_btn.pack(side='left', padx=5)
        
        self.summary_btn = tk.Button(action_frame, text="📊 Show Summary",
                                    command=self.show_summary, bg='#9b59b6',
                                    fg='white', font=('Arial', 12, 'bold'),
                                    padx=20, pady=10, cursor='hand2')
        self.summary_btn.pack(side='right', padx=5)
        
    def create_data_section(self, parent, title, attr_name, height=3):
        """Create a data entry section with skip checkbox"""
        frame = tk.LabelFrame(parent, text=title, font=('Arial', 10, 'bold'),
                            bg='#f0f0f0', fg='#2c3e50', padx=10, pady=5)
        frame.pack(fill='x', pady=(0, 8))
        
        # Skip checkbox
        skip_var = tk.BooleanVar()
        skip_check = tk.Checkbutton(frame, text="Skip this section",
                                   variable=skip_var, bg='#f0f0f0',
                                   font=('Arial', 9), fg='#7f8c8d')
        skip_check.pack(anchor='w')
        setattr(self, f"{attr_name}_skip", skip_var)
        
        # Text area
        text_widget = scrolledtext.ScrolledText(frame, height=height, 
                                               font=('Arial', 10), wrap='word')
        text_widget.pack(fill='both', expand=True)
        setattr(self, attr_name, text_widget)
        
        # Bind checkbox to disable text area
        skip_var.trace('w', lambda *args: self.toggle_text_area(text_widget, skip_var))
        
    def toggle_text_area(self, text_widget, skip_var):
        """Enable/disable text area based on skip checkbox"""
        if skip_var.get():
            text_widget.config(state='disabled', bg='#e0e0e0')
        else:
            text_widget.config(state='normal', bg='white')
    
    def load_students(self):
        """Load student list"""
        if not os.path.exists(self.list_file):
            messagebox.showerror("Error", f"{self.list_file} not found!")
            return
        
        with open(self.list_file, 'r', encoding='utf-8') as f:
            self.students = [line.strip() for line in f if line.strip()]
        
        # Find missing students
        self.missing_students = self.find_missing_students()
        
        if not self.missing_students:
            messagebox.showinfo("Complete", "All students have data!")
            self.disable_inputs()
            return
        
        self.current_index = 0
        self.load_current_student()
        
    def find_missing_students(self):
        """Find students missing both PDF and text data"""
        missing = []
        
        for student in self.students:
            pdf_exists = os.path.exists(os.path.join(self.pdf_dir, f"{student}.pdf"))
            json_exists = os.path.exists(os.path.join(self.text_dir, f"{student}.json"))
            
            if not pdf_exists and not json_exists:
                missing.append(student)
        
        return missing
    
    def load_current_student(self):
        """Load current student info"""
        if self.current_index >= len(self.missing_students):
            messagebox.showinfo("Complete", "All students processed!")
            self.disable_inputs()
            return
        
        self.current_student = self.missing_students[self.current_index]
        self.student_label.config(text=self.current_student, fg='#27ae60')
        self.progress_label.config(text=f"{self.current_index + 1}/{len(self.missing_students)}")
        
        # Clear all fields
        self.clear_all_fields()
        
        
        # Check if photo exists
        photo_exists = self.check_photo_exists()
        if photo_exists:
            self.photo_status.config(text="✓ Photo already exists", fg='#27ae60')
            self.paste_photo_btn.config(state='disabled')
        else:
            self.photo_status.config(text="", fg='#27ae60')
            self.paste_photo_btn.config(state='normal')
    
    def check_photo_exists(self):
        """Check if photo exists for current student"""
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            if os.path.exists(os.path.join(self.photo_dir, f"{self.current_student}{ext}")):
                return True
        return False
    
    def clear_all_fields(self):
        """Clear all input fields"""
        for attr in ['skills_text', 'projects_text', 'courses_text', 'other_text']:
            widget = getattr(self, attr)
            widget.config(state='normal')
            widget.delete('1.0', 'end')
            skip_var = getattr(self, f"{attr}_skip")
            skip_var.set(False)
    
    def paste_photo(self):
        """Paste photo from clipboard"""
        try:
            img = ImageGrab.grabclipboard()
            
            if img is None:
                messagebox.showerror("Error", "No image found in clipboard!\n\nPlease:\n1. Right-click on LinkedIn profile photo\n2. Select 'Copy image'\n3. Come back and click 'Paste Photo'")
                return
            
            if isinstance(img, Image.Image):
                filepath = os.path.join(self.photo_dir, f"{self.current_student}.jpg")
                img = img.convert('RGB')
                img.save(filepath, 'JPEG', quality=95)
                self.photo_status.config(text="✓ Photo saved successfully!", fg='#27ae60')
                self.paste_photo_btn.config(state='disabled')
            else:
                messagebox.showerror("Error", "Clipboard contains non-image data")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save photo: {str(e)}")
    
    def skip_photo(self):
        """Skip photo for current student"""
        self.photo_status.config(text="⊘ Photo skipped", fg='#e67e22')
        self.paste_photo_btn.config(state='disabled')
    
    def parse_projects_section(self, raw_text: str) -> List[Dict[str, str]]:
        """Parse projects from LinkedIn format text"""
        if not raw_text:
            return []
        
        projects = []
        lines = raw_text.split('\n')
        
        current_project = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('*'):
                continue
            
            # Check if this is a date line
            date_patterns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', '20']
            is_date_line = any(pattern in line for pattern in date_patterns)
            
            # Check if line starts with "Associated with"
            is_association_line = line.startswith('Associated with')
            
            if not is_date_line and not is_association_line and line:
                # Project title/description
                if current_project is None:
                    current_project = {
                        'title': line,
                        'description': '',
                        'duration': '',
                        'organization': ''
                    }
                else:
                    if current_project['description']:
                        current_project['description'] += ' ' + line
                    else:
                        current_project['description'] = line
            
            elif is_date_line and current_project:
                current_project['duration'] = line
            
            elif is_association_line and current_project:
                current_project['organization'] = line.replace('Associated with', '').strip()
                projects.append(current_project)
                current_project = None
        
        # Add last project if exists
        if current_project:
            projects.append(current_project)
        
        return projects
    
    def save_and_next(self):
        """Save current student data and move to next"""
        if not self.current_student:
            return

        # Check for a dropped/placed PDF named 'Profile.pdf' and rename it
        # to the current student's name before saving and advancing.
        self.check_and_move_profile_pdf()
        
        # Collect data
        data = {
            'student_name': self.current_student,
            'skills': None if self.skills_text_skip.get() else self.skills_text.get('1.0', 'end').strip() or None,
            'courses': None if self.courses_text_skip.get() else self.courses_text.get('1.0', 'end').strip() or None,
            'other_info': None if self.other_text_skip.get() else self.other_text.get('1.0', 'end').strip() or None
        }
        
        # Handle projects with parsing
        if not self.projects_text_skip.get():
            projects_raw = self.projects_text.get('1.0', 'end').strip()
            if projects_raw:
                data['projects'] = {
                    'raw_text': projects_raw,
                    'parsed_projects': self.parse_projects_section(projects_raw)
                }
            else:
                data['projects'] = None
        else:
            data['projects'] = None
        
        # Save to JSON
        try:
            filepath = os.path.join(self.text_dir, f"{self.current_student}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("Success", f"Data saved for {self.current_student}!")
            
            # Move to next student
            self.current_index += 1
            self.load_current_student()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")

    def save_current(self):
        """Save current student data without advancing to the next student"""
        if not self.current_student:
            return

        # Collect data (same logic as save_and_next)
        data = {
            'student_name': self.current_student,
            'skills': None if self.skills_text_skip.get() else self.skills_text.get('1.0', 'end').strip() or None,
            'courses': None if self.courses_text_skip.get() else self.courses_text.get('1.0', 'end').strip() or None,
            'other_info': None if self.other_text_skip.get() else self.other_text.get('1.0', 'end').strip() or None
        }

        # Handle projects with parsing
        if not self.projects_text_skip.get():
            projects_raw = self.projects_text.get('1.0', 'end').strip()
            if projects_raw:
                data['projects'] = {
                    'raw_text': projects_raw,
                    'parsed_projects': self.parse_projects_section(projects_raw)
                }
            else:
                data['projects'] = None
        else:
            data['projects'] = None

        # Save to JSON (do not change current_index)
        try:
            filepath = os.path.join(self.text_dir, f"{self.current_student}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            messagebox.showinfo("Success", f"Data saved for {self.current_student}!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")

    def check_and_move_profile_pdf(self):
        """If `Profile.pdf` exists in the PDFs folder, move/rename it to the
        current student's filename. Prompt before overwriting an existing file.
        This check runs only when saving & advancing (no background monitoring).
        """
        try:
            profile_src = os.path.join(self.pdf_dir, 'Profile.pdf')
            if not os.path.exists(profile_src):
                return

            target = os.path.join(self.pdf_dir, f"{self.current_student}.pdf")

            # If target exists, ask the user whether to overwrite
            if os.path.exists(target):
                if not messagebox.askyesno("Overwrite PDF?",
                                           f"{os.path.basename(target)} already exists. Overwrite?"):
                    return

            # Move (rename) the Profile.pdf to the student's filename
            shutil.move(profile_src, target)
            messagebox.showinfo("PDF Saved", f"Profile.pdf saved as {os.path.basename(target)}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to move Profile.pdf: {e}")
    
    def skip_student(self):
        """Skip current student"""
        if messagebox.askyesno("Skip Student", f"Skip {self.current_student}?"):
            self.current_index += 1
            self.load_current_student()
    
    def show_summary(self):
        """Show summary of all students"""
        complete = 0
        missing_pdf = 0
        missing_text = 0
        missing_photo = 0
        
        for student in self.students:
            pdf_exists = os.path.exists(os.path.join(self.pdf_dir, f"{student}.pdf"))
            json_exists = os.path.exists(os.path.join(self.text_dir, f"{student}.json"))
            photo_exists = False
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                if os.path.exists(os.path.join(self.photo_dir, f"{student}{ext}")):
                    photo_exists = True
                    break
            
            if (pdf_exists or json_exists) and photo_exists:
                complete += 1
            if not pdf_exists:
                missing_pdf += 1
            if not json_exists:
                missing_text += 1
            if not photo_exists:
                missing_photo += 1
        
        summary = f"""SUMMARY
{'='*40}
Total students: {len(self.students)}
Complete (data + photo): {complete}
Missing PDF: {missing_pdf}
Missing text: {missing_text}
Missing photo: {missing_photo}

Directories:
• LinkedIn PDFs: {self.pdf_dir}/
• Manual data (JSON): {self.text_dir}/
• Profile photos: {self.photo_dir}/"""
        
        messagebox.showinfo("Summary", summary)
    
    def disable_inputs(self):
        """Disable all input fields"""
        self.paste_photo_btn.config(state='disabled')
        self.skip_photo_btn.config(state='disabled')
        self.save_btn.config(state='disabled')
        self.skip_top_btn.config(state='disabled')

def main():
    root = tk.Tk()
    app = StudentOrganizerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()