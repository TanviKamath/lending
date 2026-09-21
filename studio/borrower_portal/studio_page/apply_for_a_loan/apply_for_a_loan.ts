import { computed, ref, watch } from "vue"
import { call, toast } from "frappe-ui"
import { tone, appRoute } from "@app/utils/portal"

export default function setup(context: any) {
	const { router } = context
	const showAlerts = ref(false)
	const alertsTab = ref("attention")
	const step = ref(1)
	const applicantType = ref("Individual")
	const loanProduct = ref("")
	const mobileNumber = ref("")
	const otp = ref("")
	const employmentType = ref("Salaried")
	const password = ref("")
	const companyName = ref("")
	const applicantName = ref("")
	const dateOfBirth = ref("")
	const pan = ref("")
	const applicantCountry = ref("")
	const email = ref("")
	const loanAmount = ref("")
	const proposedTenure = ref("")
	const income = ref("")

	const open = (url?: string) => {
		const to = appRoute(url)
		if (to) router.push(to)
	}

	const busy = ref(false)
	const codeSent = ref(false)
	const token = ref("")
	const accountToken = ref("")
	const offer = ref<Record<string, any>>({})

	const fail = (error: any) =>
		toast.error(String(error?.messages?.[0] || error?.message || error))

	const go = (to: number) => { step.value = to }

	const choose = (type: string) => { applicantType.value = type }

	const chooseProduct = (product: string) => { loanProduct.value = product }

	const sendCode = () => {
		busy.value = true
		call("lending.portal.apply.send_mobile_code", { mobile_number: mobileNumber.value })
			.then((result: any) => { codeSent.value = true; toast.success(result.message) })
			.catch(fail)
			.finally(() => { busy.value = false })
	}

	const confirmCode = () => {
		busy.value = true
		call("lending.portal.apply.confirm_mobile_code", {
			mobile_number: mobileNumber.value,
			otp: otp.value,
		})
			.then((result: any) => {
				if (!result.verified) { toast.error(result.message); return }
				token.value = result.token
				step.value = 5
			})
			.catch(fail)
			.finally(() => { busy.value = false })
	}

	const submit = () => {
		busy.value = true
		call("lending.portal.apply.submit_lead", {
			token: token.value,
			applicant_type: applicantType.value,
			loan_product: loanProduct.value,
			company_name: companyName.value,
			applicant_name: applicantName.value,
			date_of_birth: dateOfBirth.value,
			pan: pan.value,
			applicant_country: applicantCountry.value,
			email: email.value,
			loan_amount: loanAmount.value,
			proposed_tenure: proposedTenure.value,
			income: income.value,
			employment_type: employmentType.value,
		})
			.then((result: any) => {
				offer.value = result
				accountToken.value = result.account_token
				step.value = 6
			})
			.catch(fail)
			.finally(() => { busy.value = false })
	}

	const createAccount = () => {
		busy.value = true
		call("lending.portal.apply.create_account", {
			token: accountToken.value,
			password: password.value,
		})
			.then(() => { window.location.href = "/borrower-portal/overview" })
			.catch(fail)
			.finally(() => { busy.value = false })
	}

	return { tone, open, showAlerts, alertsTab, step, applicantType, loanProduct, mobileNumber, otp, employmentType, password, companyName, applicantName, dateOfBirth, pan, applicantCountry, email, loanAmount, proposedTenure, income, busy, codeSent, offer, go, choose, chooseProduct, sendCode, confirmCode, submit, createAccount }
}
