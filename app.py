from fpdf import FPDF
import os
import streamlit as st

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Bill Receipt', align='C', ln=True, border=0)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def generate_pdf(name, bill):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, f"Bill for: {name}", ln=True, align="C")
    pdf.cell(0, 10, f"Total Paid: {bill['total_paid']:.2f}", ln=True)
    pdf.cell(0, 10, f"Total Owed: {bill['total_owed']:.2f}", ln=True)
    pdf.cell(0, 10, "Details:", ln=True)

    for detail in bill["bill_details"]:
        pdf.cell(0, 10, f"- {detail}", ln=True)

    file_path = f"{name}_bill.pdf"
    pdf.output(file_path)
    return file_path


class SplitBillApp:
    def __init__(self):
        self.people = []
        self.expenses = []
        self.transactions = []

    def calculate_results(self):
        balances = {person: 0 for person in self.people}

        for expense in self.expenses:
            payer = expense["payer"]
            amount = expense["amount"]
            shares = expense["shares"]

            balances[payer] += amount
            for person, share in shares.items():
                balances[person] -= share

        self.transactions = balances

    def add_expense(self, reason, payer, amount, distribution_type, distribution_data):
        shares = {}

        if distribution_type == "Equal":
            split_amount = round(amount / len(self.people), 2)
            for person in self.people:
                shares[person] = split_amount

        elif distribution_type == "Unequal":
            for person, individual_share in zip(self.people, distribution_data):
                shares[person] = round(individual_share, 2)

        self.expenses.append({
            "reason": reason,
            "payer": payer,
            "amount": round(amount, 2),
            "shares": shares
        })

    def generate_bill(self, name):
        if name not in self.people:
            return None

        bill_details = []
        total_paid = sum(exp["amount"] for exp in self.expenses if exp["payer"] == name)
        total_owed = -self.transactions.get(name, 0)

        for expense in self.expenses:
            reason = expense["reason"]
            payer = expense["payer"]
            shares = expense["shares"]

            if name == payer:
                bill_details.append(f"Paid for {reason}: {expense['amount']:.2f}")
            elif name in shares:
                bill_details.append(f"Share for {reason}: {shares[name]:.2f}")

        summary = {
            "total_paid": round(total_paid, 2),
            "total_owed": round(total_owed, 2),
            "bill_details": bill_details
        }
        return summary

# Streamlit App
def main():
    st.title("Split Bill App")

    app = SplitBillApp()

    if "people" not in st.session_state:
        st.session_state.people = []
    if "expenses" not in st.session_state:
        st.session_state.expenses = []
    if "transactions" not in st.session_state:
        st.session_state.transactions = {}

    app.people = st.session_state.people
    app.expenses = st.session_state.expenses
    app.transactions = st.session_state.transactions

    # Step 1: Add participants
    with st.sidebar:
        st.header("Add Participants")
        person = st.text_input("Enter name:", key="add_person")
        if st.button("Add Participant"):
            if person and person not in st.session_state.people:
                st.session_state.people.append(person)

    if app.people:
        st.subheader("Participants")
        st.write(app.people)

        # Step 2: Add expenses
        st.header("Add an Expense")
        reason = st.text_input("Reason for expense:")
        payer = st.selectbox("Who paid?", app.people)
        amount = st.number_input("Amount spent:", min_value=0, step=0)

        distribution_type = st.radio(
            "Select Distribution Type:",
            ("Equal", "Unequal")
        )

        distribution_data = []

        if distribution_type == "Unequal":
            unequal_data = st.text_input(
                "Enter individual amounts (comma-separated, same order as participants):"
            )
            if unequal_data:
                distribution_data = list(map(float, unequal_data.split(",")))

        if st.button("Add Expense"):
            if reason and payer and amount > 0 and distribution_type:
                app.add_expense(
                    reason, payer, amount, distribution_type, distribution_data
                )
                st.session_state.expenses = app.expenses
                st.success("Expense added successfully!")
            else:
                st.error("Please fill all details correctly.")

        # Step 3: Calculate and display results
        if st.button("Calculate Results"):
            app.calculate_results()
            st.session_state.transactions = app.transactions

            st.subheader("Overall Summary")
            for person, balance in app.transactions.items():
                if balance > 0:
                    st.write(f"{person} should receive {balance:.2f}")
                elif balance < 0:
                    st.write(f"{person} owes {-balance:.2f}")
                else:
                    st.write(f"{person} is settled up.")

        # Step 4: Generate individual bills
        st.header("Generate a Bill")
        selected_person = st.selectbox("Select a person:", app.people)

        if st.button("Generate Bill"):
            bill = app.generate_bill(selected_person)
            if bill:
                st.subheader(f"Bill for {selected_person}")
                st.write(f"Total Paid: {bill['total_paid']:.2f}")
                st.write(f"Total Owed: {bill['total_owed']:.2f}")
                st.write("Details:")
                for detail in bill["bill_details"]:
                    st.write(f"- {detail}")
                
                # Generate PDF
                pdf_path = generate_pdf(selected_person, bill)
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label=f"Download {selected_person}'s Bill as PDF",
                        data=pdf_file,
                        file_name=f"{selected_person}_bill.pdf",
                        mime="application/pdf"
                    )

                # Cleanup after download
                os.remove(pdf_path)

if __name__ == "__main__":
    main()
